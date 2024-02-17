FROM nginx:1.25

RUN mkdir -p $APP_HOME/static/custom
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d