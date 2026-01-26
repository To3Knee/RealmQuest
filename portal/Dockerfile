FROM node:20-bookworm
WORKDIR /app

# Copy package info
COPY package.json package-lock.json* ./

# Install dependencies (Force to ignore lockfile conflicts)
RUN npm install --force

# Copy source code
COPY . .

# Expose Vite Port
EXPOSE 3000

# STARTUP COMMAND
# We use a shell wrapper to keep the container alive if npm fails
CMD sh -c "npm run dev -- --host 0.0.0.0 || tail -f /dev/null"
