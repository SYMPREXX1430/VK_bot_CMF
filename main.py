# -*- coding: utf-8 -*-

import vk_api, requests, json, datetime
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.upload import VkUpload
from io import BytesIO

# Токен сообщества
token = ""

# Получение токена пользователя (администратора) из файла
with open('token.txt') as tok:
    token_u = tok.readline()

vk = vk_api.VkApi(token=token)
api = vk.get_api()
longpoll = VkLongPoll(vk)
peer_id = -0 # ID сообщества с символом "-" (8 символов)

vk_u = vk_api.VkApi(token=token_u)
api_u = vk_u.get_api()

# Список с URL-ами
urls = []

# Список с ID вложений
attachments_w = []
attachments_m = []

# Список с ID разрешенных пользователей
users = []

# Сообщение для теста, сюда же добавляем тэги
message = ''

# Сообщение для публикации, формируется на основе message
message_to_send = ''

# Получаем URL изображения из сообщения с МАКСИМАЛЬНЫМ разрешением, присланного пользователем
def get_url(msg_info):
    global urls
    photo_urls = msg_info['items'][0]['attachments']
    photo_quality = ['w', 'z', 'y', 'x', 'm', 's']
    qualities = []
    for attachments in photo_urls:
        for pq in photo_quality:
            for sizes in attachments['photo']['sizes']:
                if sizes['type'] in pq:
                    qualities.append(sizes['url'])
        urls.append(qualities[0])
        qualities = []
    return urls

# Функция для получения ID фото (сообщения)
def messages_upload_photo(upload, url):
    img = requests.get(url).content
    f = BytesIO(img)
    response = upload.photo_messages(f)[0]
    owner_id = response['owner_id']
    photo_id = response['id']
    access_key = response['access_key']
    return f'photo{owner_id}_{photo_id}_{access_key}'

# Функция для получения ID фото (стена)
def wall_upload_photo(upload, url):
    img = requests.get(url).content
    f = BytesIO(img)
    response = upload.photo_wall(f, group_id = (-1)*peer_id)[0]
    owner_id = response['owner_id']
    photo_id = response['id']
    return f'photo{owner_id}_{photo_id}'

# Тестовая процедура для проверки поста
def test_post(user_id, peer_id, message, attachment):
    api.messages.send(
        user_id = user_id,
        random_id = 0,
        peer_id = peer_id,
        message = message,
        attachment = attachment)

# Генератор клавиатур
def get_keyboard(buttons):
    nb = []
    color = ''
    for i in range(len(buttons)):
        nb.append([])
        for k in range(len(buttons[i])):
            nb[i].append(None)
    for i in range(len(buttons)):
        for k in range(len(buttons[i])):
            text = buttons[i][k][0]
            color = {'зеленый': 'positive', 'красный': 'negative', 'синий': 'primary'}[buttons[i][k][1]]
            nb[i][k] = {"action": {"type": "text", "payload": "{\"button\": \"" + "1" + "\"}", "label": f"{text}"}, "color": f"{color}"}
    first_keyboard = {'one_time': False, 'buttons': nb}
    first_keyboard = json.dumps(first_keyboard, ensure_ascii=False).encode('utf-8')
    first_keyboard = str(first_keyboard.decode('utf-8'))
    return first_keyboard

# Отправка клавиатуры
def send_keyboard(user_id, text, key):
    api.messages.send(user_id = user_id, message = text, keyboard = key, random_id = 0)

# Клавиатура с тэгами
tag_key = get_keyboard([
    [('Hashtag1', 'синий'), ('-Hashtag1', 'красный'), ('Hashtag2', 'синий'), ('-Hashtag2', 'красный')],
    [('Hashtag3', 'синий'), ('-Hashtag3', 'красный'), ('Enter', 'синий'), ('-Enter', 'красный')],
    [('Test', 'зеленый'), ('Post', 'синий')]
])

# Клавиатура с временем публикации
time_key = get_keyboard([
    [('7', 'синий'), ('12', 'синий')],
    [('15', 'синий'), ('18', 'синий')],
    [('19', 'синий'), ('20', 'синий')],
    [('22', 'синий'), ('Publish', 'зеленый')]
])

buttons = ['Hashtag1', 'Hashtag2', 'Hashtag3', 'Enter',
           '-Hashtag1', '-Hashtag2', '-Hashtag3', '-Enter',
           'Test', 'Post',
           '7', '12', '15', '18', '19', '20', '22', 'Publish', 'старт']

# Определяем постим сегодня или завтра, а также unix_time
def get_unix_time(post_hour):
    data_time_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    data_now = data_time_now.date()

    # Заказчику нужна была возможность откладывания поста в зависимости от текущего времени по МСК
    # Ниже предоставлен код для откладывания поста в зависимости от текущего времени в своем часом поясе

    """
    time_now = data_time_now.time()
    hour_now = str(time_now).split(':')[0]
    if int(post_hour) <= int(hour_now):
        new_data_post = str(data_now + datetime.timedelta(days=1))
        datetime_object = datetime.datetime.strptime(new_data_post + ' ' + post_hour + ':00', '%Y-%m-%d %H:%M')
        unix_time_datetime_object = datetime_object.timestamp()
    elif int(post_hour) > int(hour_now):
        datetime_object = datetime.datetime.strptime(str(data_now) + ' ' + post_hour + ':00', '%Y-%m-%d %H:%M')
        unix_time_datetime_object = datetime_object.timestamp()
    """

    new_data_post = str(data_now + datetime.timedelta(days=1))
    datetime_object = datetime.datetime.strptime(new_data_post + ' ' + post_hour + ':00', '%Y-%m-%d %H:%M')
    unix_time_datetime_object = datetime_object.timestamp()
    return int(unix_time_datetime_object)

def main():
    global message
    while True:
        try:
            # Комментарий, который будет прилагаться к фото, может быть пустым
            msg_text = ''
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    user_id = event.user_id
                    if user_id in users:

                        # Получаем msg_info
                        msg_info = api.messages.getById(message_ids=event.message_id)
                        print('msg_info = ', msg_info)

                        upload = VkUpload(api)
                        upload_u = VkUpload(api_u)

                        # Сообщение, на которое триггерится бот
                        msg = event.text

                        # Если есть фото в сообщении, добавляем URL в attachments, также добавляем сообщение в msg_text
                        if msg_info['items'][0]['attachments'] != []:
                            if msg_info['items'][0]['attachments'][0]['type'] == 'photo':
                                get_url(msg_info)
                                for url in urls:
                                    attachments_m.append(messages_upload_photo(upload, url))
                                    attachments_w.append(wall_upload_photo(upload_u, url))
                                msg_text = msg_info['items'][0]['text']

                        # Добавляем сообщение в msg_text, если текст не кнопка и не ссылка
                        elif msg not in buttons and not msg_info['items'][0]['text'].startswith('https://'):
                            msg_text = msg_info['items'][0]['text']

                        # Если получили ссылку, добавляем ее в message_copyright
                        if msg_info['items'][0]['text'].startswith('https://'):
                            message_copyright = msg_info['items'][0]['text']
                        else:
                            message_copyright = None

                        # Отправка стартовой клавиатуры, если пользователь есть в списке
                        if msg == 'старт':
                            send_keyboard(user_id, 'Выберите тэги', tag_key)

                        # Формировка тэгов на основе конструктора
                        if msg == 'Hashtag1':
                            message += '#Hashtag1 '
                            send_keyboard(user_id, 'Тэг Hashtag1 добавлен', tag_key)
                        if msg == '-Hashtag1':
                            message = message.replace('#Hashtag1 ', '', 1)
                            send_keyboard(user_id, 'Тэг  Hashtag1 удален', tag_key)
                        if msg == 'Hashtag2':
                            message += '#Hashtag2 '
                            send_keyboard(user_id, 'Тэг #Hashtag2 добавлен', tag_key)
                        if msg == '-Hashtag2':
                            message = message.replace('#Hashtag2 ', '', 1)
                            send_keyboard(user_id, 'Тэг #Hashtag2 удален', tag_key)
                        if msg == 'Hashtag3':
                            message += '#Hashtag3 '
                            send_keyboard(user_id, 'Тэг #Hashtag3 добавлен', tag_key)
                        if msg == '-Hashtag3':
                            message = message.replace('#Hashtag3 ', '', 1)
                            send_keyboard(user_id, 'Тэг #Hashtag3 удален', tag_key)
                        if msg == 'Enter':
                            message += '\n'
                            send_keyboard(user_id, 'Переход на новую строку добавлен', tag_key)
                        if msg == '-Enter':
                            message = message[::-1]
                            message = message.replace('\n', '', 1)
                            message = message[::-1]
                            send_keyboard(user_id, 'Переход на новую строку удален', tag_key)

                        # Запуск проверки сообщения
                        if msg == 'Test':
                            if msg_text != '':
                                message_to_send = msg_text + '\n\n' + message
                            else:
                                message_to_send = message
                            test_post(user_id, peer_id, message_to_send, attachments_m)

                        # Отправка клавиатуры со временем публикации
                        if msg == 'Post':
                            send_keyboard(user_id, 'Выберите время публикации', time_key)

                        # Выбор времени публикации
                        if msg == '7':
                            publish_date = get_unix_time('7')
                            send_keyboard(user_id, 'Выбрано время публикации 7:00', time_key)
                        if msg == '12':
                            publish_date = get_unix_time('12')
                            send_keyboard(user_id, 'Выбрано время публикации 12:00', time_key)
                        if msg == '15':
                            publish_date = get_unix_time('15')
                            send_keyboard(user_id, 'Выбрано время публикации 15:00', time_key)
                        if msg == '18':
                            publish_date = get_unix_time('18')
                            send_keyboard(user_id, 'Выбрано время публикации 18:00', time_key)
                        if msg == '19':
                            publish_date = get_unix_time('19')
                            send_keyboard(user_id, 'Выбрано время публикации 19:00', time_key)
                        if msg == '20':
                            publish_date = get_unix_time('20')
                            send_keyboard(user_id, 'Выбрано время публикации 20:00', time_key)
                        if msg == '22':
                            publish_date = get_unix_time('22')
                            send_keyboard(user_id, 'Выбрано время публикации 22:00', time_key)

                        # Публикуем пост по отложенному времени
                        if msg == 'Publish':
                            try:
                                api_u.wall.post(owner_id=peer_id, from_group=1, message=message_to_send,
                                                attachments=attachments_w,
                                                publish_date=publish_date,
                                                copyright=message_copyright)
                            # Если пост есть в предложке, добавляем еще сутки
                            except Exception as ex:
                                if str(ex).startswith('[214]'):
                                    publish_date += 86400
                                    api_u.wall.post(owner_id=peer_id, from_group=1, message=message_to_send,
                                                    attachments=attachments_w,
                                                    publish_date=publish_date,
                                                    copyright=message_copyright)
                            finally:
                                send_keyboard(user_id, 'Пост опубликован', tag_key)
                                # Добавление фото в альбом в зависимости от тэгов
                                for url in urls:
                                    img = requests.get(url).content
                                    f = BytesIO(img)
                                    if '#Hashtag1' in message:
                                        upload_u.photo(f, album_id=1, group_id=(-1) * peer_id)
                                    elif '#Hashtag2' in message:
                                        upload_u.photo(f, album_id=2, group_id=(-1) * peer_id)
                                    elif '#Hashtag3' in message:
                                        upload_u.photo(f, album_id=3, group_id=(-1) * peer_id)

                                message_to_send = ''
                                message = ''
                                msg_text = ''
                                attachments_m.clear()
                                attachments_w.clear()
                                urls.clear()
        except Exception as ex:
            print(ex)
            pass


if __name__ == '__main__':
    main()