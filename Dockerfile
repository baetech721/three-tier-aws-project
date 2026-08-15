FROM nginx:latest
COPY . /usr/share/nginx/html
copy nginx.conf /etc/nginx/conf.d/default.conf
