FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Fix npm permissions and install dependencies
RUN chown -R node:node /app && \
    mkdir -p /home/node/.npm && \
    chown -R node:node /home/node/.npm

USER node

RUN npm install
RUN npm install react-markdown
RUN npm i react-markdown remark-gfm

# Copy source files (must be done as root to copy from host)
USER root
COPY --chown=node:node . .

USER node

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

CMD ["nginx", "-g", "daemon off;"]
