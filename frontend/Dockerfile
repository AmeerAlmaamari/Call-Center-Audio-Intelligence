FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
RUN npm install

COPY frontend /app/frontend

EXPOSE 5173

CMD ["sleep", "infinity"]
