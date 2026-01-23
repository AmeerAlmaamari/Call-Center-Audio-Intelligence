import { useState, useEffect, useRef, useCallback } from "react"
import { GoogleGenAI, Modality } from "@google/genai"
import { Phone, PhoneOff, Mic, MicOff, Bot, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { createPCMBlob, decodeAudioData, decodeFromBase64, resampleAudio } from "@/lib/audioUtils"

interface Message {
  role: "user" | "agent" | "system"
  text: string
  timestamp: Date
}

interface CallStatus {
  isConnected: boolean
  isMuted: boolean
  isThinking: boolean
  currentTurn: "user" | "agent" | "none"
}

const SYSTEM_INSTRUCTION = `
You are a professional AI Sales Agent for a call center. Your name is "Alex".
Your goal is to handle customer inquiries, provide support, and help customers with their needs.

KEY RULES:
1. LANGUAGE: Always respond in the EXACT same language the user uses. If they speak Arabic, respond in Arabic. If English, use English.
2. PERSONALITY: Helpful, friendly, empathetic, and professional.
3. BE CONCISE: Keep responses natural for a phone conversation - not too long.
4. SALES: If the user seems interested in a solution, recommend products or services.
5. SUPPORT: Help resolve customer issues efficiently and professionally.

You are currently operating in a call center dashboard for audio intelligence analysis.
`

export default function VoiceAgent() {
  const [messages, setMessages] = useState<Message[]>([])
  const [status, setStatus] = useState<CallStatus>({
    isConnected: false,
    isMuted: false,
    isThinking: false,
    currentTurn: "none",
  })
  const [error, setError] = useState<string | null>(null)
  const [callDuration, setCallDuration] = useState(0)

  const inputAudioCtx = useRef<AudioContext | null>(null)
  const outputAudioCtx = useRef<AudioContext | null>(null)
  const outputNode = useRef<GainNode | null>(null)
  const nextStartTime = useRef<number>(0)
  const sources = useRef<Set<AudioBufferSourceNode>>(new Set())
  const activeStream = useRef<MediaStream | null>(null)
  const sessionRef = useRef<any>(null)
  const inputSource = useRef<MediaStreamAudioSourceNode | null>(null)
  const inputProcessor = useRef<ScriptProcessorNode | null>(null)
  const isSessionActive = useRef(false)
  const isMutedRef = useRef(false)
  const callTimerRef = useRef<NodeJS.Timeout | null>(null)

  const currentInputTranscription = useRef("")
  const currentOutputTranscription = useRef("")

  const API_KEY = import.meta.env.VITE_GEMINI_API_KEY

  useEffect(() => {
    if (!API_KEY) {
      setError("Gemini API Key is missing. Please set VITE_GEMINI_API_KEY in your .env file.")
    }
  }, [API_KEY])

  useEffect(() => {
    return () => {
      cleanupConnection()
    }
  }, [])

  const initializeAudio = async () => {
    if (!inputAudioCtx.current) {
      inputAudioCtx.current = new (window.AudioContext || (window as any).webkitAudioContext)()
    }
    if (!outputAudioCtx.current) {
      outputAudioCtx.current = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 24000,
      })
      outputNode.current = outputAudioCtx.current.createGain()
      outputNode.current.connect(outputAudioCtx.current.destination)
    }
  }

  const addMessage = useCallback((role: "user" | "agent" | "system", text: string) => {
    setMessages((prev) => [...prev, { role, text, timestamp: new Date() }])
  }, [])

  const stopAllAudio = () => {
    sources.current.forEach((source) => {
      try {
        source.stop()
      } catch (e) {}
    })
    sources.current.clear()
    nextStartTime.current = 0
  }

  const stopInputProcessing = () => {
    if (inputProcessor.current) {
      inputProcessor.current.onaudioprocess = null
      inputProcessor.current.disconnect()
      inputProcessor.current = null
    }
    inputSource.current?.disconnect()
    inputSource.current = null
  }

  const cleanupConnection = () => {
    isSessionActive.current = false
    stopInputProcessing()
    activeStream.current?.getTracks().forEach((track) => track.stop())
    activeStream.current = null
    stopAllAudio()
    sessionRef.current = null
    if (callTimerRef.current) {
      clearInterval(callTimerRef.current)
      callTimerRef.current = null
    }
  }

  const handleCall = async () => {
    if (status.isConnected) {
      sessionRef.current?.close()
      cleanupConnection()
      setStatus((prev) => ({ ...prev, isConnected: false, currentTurn: "none" }))
      addMessage("system", "Call ended.")
      setCallDuration(0)
      return
    }

    if (!API_KEY) {
      setError("API Key is missing")
      return
    }

    try {
      setError(null)
      await initializeAudio()
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      activeStream.current = stream

      const ai = new GoogleGenAI({ apiKey: API_KEY })

      const sessionPromise = ai.live.connect({
        model: "gemini-2.5-flash-native-audio-preview-12-2025",
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: SYSTEM_INSTRUCTION,
          speechConfig: {
            voiceConfig: { prebuiltVoiceConfig: { voiceName: "Kore" } },
          },
          inputAudioTranscription: {},
          outputAudioTranscription: {},
        },
        callbacks: {
          onopen: () => {
            isSessionActive.current = true
            setStatus((prev) => ({ ...prev, isConnected: true }))
            addMessage("system", "Connected to AI Agent. How can I help you today?")

            callTimerRef.current = setInterval(() => {
              setCallDuration((prev) => prev + 1)
            }, 1000)

            const source = inputAudioCtx.current!.createMediaStreamSource(stream)
            const scriptProcessor = inputAudioCtx.current!.createScriptProcessor(4096, 1, 1)
            inputSource.current = source
            inputProcessor.current = scriptProcessor

            scriptProcessor.onaudioprocess = (e) => {
              if (!isSessionActive.current || isMutedRef.current) return
              const inputData = e.inputBuffer.getChannelData(0)
              const sourceSampleRate = inputAudioCtx.current!.sampleRate
              const resampled = resampleAudio(inputData, sourceSampleRate, 16000)
              const pcmData = createPCMBlob(resampled)

              const session = sessionRef.current
              if (!session) return
              try {
                session.sendRealtimeInput({
                  media: { data: pcmData, mimeType: "audio/pcm;rate=16000" },
                })
              } catch (err) {
                console.warn("Realtime input send failed:", err)
              }
            }

            source.connect(scriptProcessor)
            scriptProcessor.connect(inputAudioCtx.current!.destination)
          },
          onmessage: async (message: any) => {
            if (message.serverContent?.inputTranscription) {
              currentInputTranscription.current += message.serverContent.inputTranscription.text
            }
            if (message.serverContent?.outputTranscription) {
              currentOutputTranscription.current += message.serverContent.outputTranscription.text
            }

            if (message.serverContent?.turnComplete) {
              if (currentInputTranscription.current) {
                addMessage("user", currentInputTranscription.current)
                currentInputTranscription.current = ""
              }
              if (currentOutputTranscription.current) {
                addMessage("agent", currentOutputTranscription.current)
                currentOutputTranscription.current = ""
              }
            }

            const audioData = message.serverContent?.modelTurn?.parts?.[0]?.inlineData?.data
            if (audioData) {
              setStatus((prev) => ({ ...prev, currentTurn: "agent" }))
              const buffer = await decodeAudioData(
                decodeFromBase64(audioData),
                outputAudioCtx.current!,
                24000
              )
              const source = outputAudioCtx.current!.createBufferSource()
              source.buffer = buffer
              source.connect(outputNode.current!)

              nextStartTime.current = Math.max(
                nextStartTime.current,
                outputAudioCtx.current!.currentTime
              )
              source.start(nextStartTime.current)
              nextStartTime.current += buffer.duration

              source.onended = () => {
                sources.current.delete(source)
                if (sources.current.size === 0) {
                  setStatus((prev) => ({ ...prev, currentTurn: "none" }))
                }
              }
              sources.current.add(source)
            }

            if (message.serverContent?.interrupted) {
              stopAllAudio()
            }
          },
          onerror: (e: any) => {
            console.error("Gemini error:", e)
            setError("Connection error occurred. Please try again.")
            setStatus((prev) => ({ ...prev, isConnected: false }))
            cleanupConnection()
          },
          onclose: () => {
            setStatus((prev) => ({ ...prev, isConnected: false }))
            cleanupConnection()
          },
        },
      })

      sessionPromise.then((session: any) => {
        sessionRef.current = session
      })

      await sessionPromise
    } catch (err: any) {
      cleanupConnection()
      setError(err.message || "Failed to start call")
    }
  }

  const toggleMute = () => {
    setStatus((prev) => {
      isMutedRef.current = !prev.isMuted
      return { ...prev, isMuted: !prev.isMuted }
    })
  }

  const formatDuration = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Voice Agent</h1>
          <p className="text-muted-foreground">
            Real-time AI-powered customer service agent using Gemini Live API
          </p>
        </div>
        <Badge
          variant={status.isConnected ? "default" : "secondary"}
          className={status.isConnected ? "bg-green-500" : ""}
        >
          {status.isConnected ? "Connected" : "Offline"}
        </Badge>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card className="overflow-hidden">
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 aspect-video flex items-center justify-center relative">
              <div
                className={`flex flex-col items-center transition-all duration-500 ${
                  status.isConnected ? "scale-110" : "scale-100 opacity-60"
                }`}
              >
                <div
                  className={`w-32 h-32 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center relative ${
                    status.currentTurn === "agent" ? "animate-pulse" : ""
                  }`}
                >
                  <Bot className="h-16 w-16 text-white" />
                  {status.currentTurn === "agent" && (
                    <div className="absolute inset-0 rounded-full border-4 border-blue-400 opacity-50 animate-ping" />
                  )}
                </div>
                <p className="mt-6 text-white text-lg font-light">
                  {status.isConnected
                    ? status.currentTurn === "agent"
                      ? "AI is speaking..."
                      : "Listening..."
                    : "Ready to start call"}
                </p>
              </div>

              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 bg-white/10 backdrop-blur-md px-6 py-3 rounded-full border border-white/20">
                <Button
                  variant={status.isMuted ? "destructive" : "ghost"}
                  size="icon"
                  onClick={toggleMute}
                  disabled={!status.isConnected}
                  className={!status.isMuted ? "text-white hover:bg-white/20" : ""}
                >
                  {status.isMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
                </Button>

                <Button
                  onClick={handleCall}
                  className={`px-8 ${
                    status.isConnected
                      ? "bg-red-600 hover:bg-red-700"
                      : "bg-green-500 hover:bg-green-600"
                  }`}
                >
                  {status.isConnected ? (
                    <>
                      <PhoneOff className="h-4 w-4 mr-2" />
                      End Call
                    </>
                  ) : (
                    <>
                      <Phone className="h-4 w-4 mr-2" />
                      Start Call
                    </>
                  )}
                </Button>
              </div>

              <div className="absolute top-4 right-4 bg-black/50 px-3 py-1 rounded-full text-white text-sm font-mono">
                {formatDuration(callDuration)}
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Conversation Transcript</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80 overflow-y-auto space-y-3 p-2">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                    <Bot className="h-12 w-12 mb-2 opacity-50" />
                    <p>Conversation transcript will appear here...</p>
                  </div>
                ) : (
                  messages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[80%] p-3 rounded-2xl ${
                          msg.role === "user"
                            ? "bg-blue-600 text-white rounded-tr-none"
                            : msg.role === "system"
                            ? "bg-amber-50 text-amber-800 border border-amber-200 text-sm text-center mx-auto"
                            : "bg-gray-100 text-gray-800 rounded-tl-none"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          {msg.role === "agent" && <Bot className="h-4 w-4" />}
                          {msg.role === "user" && <User className="h-4 w-4" />}
                        </div>
                        <p className="text-sm leading-relaxed">{msg.text}</p>
                        <span
                          className={`text-xs mt-1 block opacity-70 ${
                            msg.role === "user" ? "text-right" : "text-left"
                          }`}
                        >
                          {msg.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-blue-500" />
                AI Agent: Alex
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                  <Bot className="h-8 w-8 text-white" />
                </div>
                <div>
                  <p className="font-semibold">Alex</p>
                  <p className="text-sm text-muted-foreground">AI Sales Agent</p>
                  <Badge variant="outline" className="mt-1">
                    Gemini 2.5 Flash
                  </Badge>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-gray-50 p-2 rounded">
                  <p className="text-muted-foreground text-xs">Languages</p>
                  <p className="font-medium">Multi-lingual</p>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <p className="text-muted-foreground text-xs">Response</p>
                  <p className="font-medium">Real-time</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Capabilities</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  Real-time voice conversation
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  Multi-language support
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  Natural barge-in handling
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  Emotional tone awareness
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  Live transcription
                </li>
              </ul>
            </CardContent>
          </Card>

          <Card className="bg-blue-600 text-white">
            <CardContent className="pt-6">
              <h4 className="font-bold mb-2">Powered by Gemini Live API</h4>
              <p className="text-sm text-blue-100 mb-4">
                Experience natural, low-latency voice conversations with AI using Google's
                latest native audio model.
              </p>
              <Badge variant="secondary" className="bg-white/20 text-white">
                Native Audio Processing
              </Badge>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
