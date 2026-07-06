# docker/frontend.Dockerfile
#
# Purpose: build an image that runs your React dev server inside a
# container. We're using dev mode (not a production build) to match
# what you've been doing locally with `npm run dev` -- simpler to
# reason about while learning; a real production deployment would use
# a different, optimized build step, worth revisiting later.

# Official Node.js image -- "slim" for a smaller image, same idea as
# the Python backend image.
FROM node:20-slim

WORKDIR /app

# Same caching trick as the backend: copy ONLY the dependency
# manifests first, install, THEN copy the rest of the code. Changing
# your React component code won't force a slow "npm install" to re-run.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ ./

EXPOSE 5173

# --host 0.0.0.0 is IMPORTANT here: by default, Vite's dev server only
# listens for connections from "localhost" INSIDE the container, which
# would make it unreachable from your actual browser outside the
# container. Binding to 0.0.0.0 means "accept connections from
# anywhere", which is what lets Docker's port-forwarding (set up in
# docker-compose.yml) actually reach it.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
