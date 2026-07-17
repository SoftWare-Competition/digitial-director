import sys
with open('/etc/nginx/sites-enabled/photo-gallery', 'rb') as f:
    data = f.read()
marker = b'    location /static/model/'
insert_block = b'    location /static/audio/ {\n        alias /opt/backend/audio/;\n        expires 1d;\n    }\n\n'
data = data.replace(marker, insert_block + marker)
with open('/etc/nginx/sites-enabled/photo-gallery', 'wb') as f:
    f.write(data)
print('OK')
