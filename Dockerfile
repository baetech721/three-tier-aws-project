FROM nginx:latest
RUN apt-get update && apt-get upgrade -y
COPY . /usr/share/nginx/html
copy nginx.conf /etc/nginx/conf.d/default.conf
