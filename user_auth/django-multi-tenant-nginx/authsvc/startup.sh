#!/bin/sh

# 等待数据库就绪
echo "Waiting for database to be ready..."
while ! nc -z $MYSQL_HOST $MYSQL_PORT; do
  sleep 1
done

echo "Database is ready!"

# 执行数据库迁移
echo "Running database migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# 创建超级用户（如果不存在）
echo "Creating superuser if not exists..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); \
if not User.objects.filter(username='admin').exists(): \
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpassword'); \
    print('Superuser created successfully'); \
else: \
    print('Superuser already exists')" | python manage.py shell

# 启动Gunicorn服务器
echo "Starting Gunicorn server..."
exec gunicorn -b 0.0.0.0:8000 authsvc.wsgi:application --access-logfile - --error-logfile - --capture-output --log-level=info --workers 2 --threads 4