FROM node:20-alpine

WORKDIR /app

# NEXT_PUBLIC_* vars are inlined at build time. The browser hits the
# host-exposed backend port, so the default localhost:8000 works.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
