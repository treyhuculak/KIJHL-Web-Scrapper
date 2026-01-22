# Use a lightweight NGINX image
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy your single HTML file to the NGINX web root
COPY index.html /usr/share/nginx/html/index.html

# Expose the port Cloud Run expects (8080 by default)
EXPOSE 8080

# Start NGINX
CMD ["nginx", "-g", "daemon off;"]