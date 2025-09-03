FROM openresty/openresty:1.25.3.1-1-bookworm-fat

RUN /usr/local/openresty/bin/opm get ledgetech/lua-resty-http

COPY dispatcher/nginx.conf /usr/local/openresty/nginx/conf/nginx.conf

EXPOSE 8080
CMD ["/usr/local/openresty/bin/openresty", "-g", "daemon off;"]