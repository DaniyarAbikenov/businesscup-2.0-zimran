FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit --no-fund
COPY . .
EXPOSE 5173
# Dev server with hot module reload. Source is bind-mounted by docker-compose.yml.
CMD ["npm", "run", "dev"]
