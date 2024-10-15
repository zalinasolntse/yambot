import multiprocessing # Импортируем модуль для работы с многопоточностью
import os # Импортируем модуль для работы с операционной системой
from time import sleep # Импортируем функцию sleep для паузы в выполнении
from requests import post

# Импортируем функцию для загрузки переменных окружения
from dotenv import load_dotenv 

UPDATES_URL = "https://botapi.messenger.yandex.net/bot/v1/messages/getUpdates"  # URL для получения обновлений
SEND_TEXT_URL = "https://botapi.messenger.yandex.net/bot/v1/messages/sendText/"  # URL для отправки текста

# Импортируем функции из API
from api.gpt_api import send_translate_request, send_art_request, get_art_response
from api.tracker_api import create_ticket
from yambot.yambot import MessengerBot

# Загружаем переменные окружения из файла .env( В НЕМ НАХОДЯТСЯ ВСЕ ТОКЕНЫ И КЛЮЧИ API)
load_dotenv()
yb = MessengerBot(os.getenv('BOT_KEY'))  # Создаем экземпляр бота с ключом из переменных окружения
main_menu = [] # Инициализируем основные структуры данных
translate_requests = {} # Основное меню
pass_requests = {} # Словарь для хранения запросов на перевод
art_requests = {} # Словарь для хранения запросов на генерацию изображения
art_queue = {} 

level = '1'

# Функция которая периодически запрашивает наличие новых сообщений для бота. В качестве аргумента передаем функцию
# которая будет вызвана при получении новых сообщений
def start_pooling(bot):
    # Первичный запрос для получения ID последнего сообщения. Чтобы не обрабатывать все сообщения чата, пока бот
    # выключен. В реальном использовании, возможно предусмотреть друое поведение и обрабатывать все сообщения
    last_update_id = -1
    request_body = {'limit': 100, 'offset': 0}
    response = post(UPDATES_URL, json=request_body, headers=yb)
    updates = response.json()['updates']
    if len(updates) > 0:
        updates = response.json()['updates']
        last_update_id = int(updates[len(updates) - 1]['update_id'])  # Получаем ID последнего сообщения

    #  Запускаем цикл постояных запросов на новые сообщения
    while True:
        # Запрашиваем только новые сообщения. Будут получены сообщения только с ID на 1 больше последнего полученного
        # сообщения
        request_body = {'limit': 100, 'offset': last_update_id + 1}

        response = post(UPDATES_URL, json=request_body, headers=yb)
        updates = response.json()['updates']  # из ответа получаем массив новых сообщений

        if len(updates) > 0:
            # Для последующих запросов цикла сохраняем ID последнего сообщения
            last_update_id = int(updates[len(updates) - 1]['update_id'])

            # Для каждого сообщения вызываем функцию которая будет обрабатывать это сообщение
            for update in updates:
                bot(update)
        sleep(1)  # Ждем 1 секунду прежде чем повторить цикл


@yb.add_handler(command='/debug')
def show_handlers(update): #Команда для отображения всех обработчиков.
    yb.list_handlers()


@yb.add_handler(button='/translate')
def translate_button(update): #Обработчик кнопки перевода. Запрашивает текст для перевода.
    yb.send_message(f'Введите текст для перевода:', update)
    translate_requests.update({f'{update.from_m.from_id}': update})  # Сохраняем запрос


@yb.add_handler(button='/pass')
def pass_button(update): #Обработчик кнопки пропуска. Запрашивает имя и фамилию для заказа пропуска.
    yb.send_message(f'Введите имя и фамилию для заказа пропуска:', update)
    pass_requests.update({f'{update.from_m.from_id}': update}) # Сохраняем запрос



@yb.add_handler(button='/pass_yes')
def pass_yes(update):
    res = create_ticket(update.callback_data['name']) #Обработчик подтверждения заказа пропуска.
    yb.send_message(f"Заявка на пропуск оформлена: https://tracker.yandex.ru/{res['key']}", update)
    send_menu(update, main_menu) # Возвращаем в основное меню


@yb.add_handler(button='/pass_no')
def pass_no(update): #Обработчик отмены заказа пропуска.
    yb.send_message(f'"Заказ пропуска отменен', update)
    send_menu(update, main_menu) # Возвращаем в основное меню


@yb.add_handler(button='/gpt')
def art_button(update): #Обработчик кнопки генерации изображения. Запрашивает текст для генерации.
    yb.send_message(f'Введите текст для генерации изображения:', update)
    art_requests.update({f'{update.from_m.from_id}': update}) # Сохраняем запрос


@yb.add_handler(button='/art_yes')
def art_yes(update): #Обработчик подтверждения генерации изображения.
    response = send_art_request(update.callback_data['text']) # Отправляем запрос на генерацию изображения
    print(f"Art response: {response}")
    try:
        yb.send_message(f"Отправлен запрос на генерацию изображения. Id запроса: {response['id']}", update)
        art_queue.update({f"{response['id']}": update}) # Сохраняем запрос в очередь
    except KeyError:
        yb.send_message(f"Ошибка: {response['error']}", update) # Обработка ошибки
        send_menu(update, main_menu) # Возвращаем в основное меню


@yb.add_handler(button='/art_no') 
def art_no(update): #Обработчик отмены генерации изображения
    yb.send_message(f'"Генерация изображения отменена', update)
    send_menu(update, main_menu) # Возвращаем в основное меню


@yb.add_handler(any=True)
def process_any(update): #Обработчик всех других сообщений.
    if f'{update.from_m.from_id}' in translate_requests:
        response = send_translate_request(update.text) # Отправляем текст на перевод
        text = response['translations'][0]['text'] #Получаем перевод
        yb.send_message(f"Перевод:\n```{text}```", update) #Отправляем перевод пользователю
        translate_requests.pop(f'{update.from_m.from_id}', None) # Удаляем запрос
        send_menu(update, main_menu)
    elif f'{update.from_m.from_id}' in pass_requests: # Создаем кнопки для подтверждения или отмены заказа пропуска
        button_pass_yes = {'text': 'Да', 'callback_data': {'cmd': '/pass_yes', 'name': update.text}}
        button_pass_no = {'text': 'Нет', 'callback_data': {'cmd': '/pass_no'}}
        yb.send_inline_keyboard(
            f'Заказать пропуск для: {update.text}?',
            [button_pass_yes, button_pass_no],
            update
        )
        pass_requests.pop(f'{update.from_m.from_id}', None) # Удаляем запрос

    elif f'{update.from_m.from_id}' in art_requests: # Создаем кнопки для подтверждения или отмены генерации изображения
        button_art_yes = {'text': 'Да', 'callback_data': {'cmd': '/art_yes', 'text': update.text}}
        button_art_no = {'text': 'Нет', 'callback_data': {'cmd': '/art_no'}}
        yb.send_inline_keyboard(
            f'Сгенерировать изображение по запросу: {update.text}?',
            [button_art_yes, button_art_no],
            update
        )
        art_requests.pop(f'{update.from_m.from_id}', None)  # Удаляем запрос
    else:
        send_menu(update, main_menu) # Если нет активных запросов, возвращаем в меню


def art_thread(art_q, menu): #Фоновый поток для обработки очереди генерации изображений.
    #  global art_queue
    while True:
        print("Art queue size: ", len(art_q)) # Выводим размер очереди
        for art_request in art_q.keys():
            response = get_art_response(art_request) # Получаем ответ о готовности изображения
            if response['done']:
                yb.send_message("Изображение готово", art_q[art_request]) # Уведомляем пользователя
                yb.send_image(response['response']['image'], art_q[art_request]) # Отправляем изображение
                send_menu(art_q[art_request], menu) # Возвращаем в меню
                art_q.pop(art_request, None) # Удаляем обработанный запрос
                break
            
            # Если условие в предыдущем блоке не выполнено, выполняем этот код
            else:
                print(art_q)   # Выводим содержимое очереди art_q в консоль для отладки
    # Отправляем сообщение пользователю о том, что идет процесс генерации
                yb.send_message("Генерируется...", art_q[art_request])
        # print("Sleeping")
        sleep(10) # Приостанавливаем выполнение на 10 секунд


def build_menu(): # Создаем кнопки для меню с текстом и соответствующими командами
    button_help = {'text': 'Главное меню', 'callback_data': {'cmd': '/help'}}
    button_hello = {'text': 'Заявки на формы', 'callback_data': {'cmd': '/hello'}}
    button_art = {'text': 'Генерация изображения', 'callback_data': {'cmd': '/art'}}
    button_translate = {'text': 'Перевод', 'callback_data': {'cmd': '/translate'}}
    button_pass = {'text': 'Пропуск', 'callback_data': {'cmd': '/pass'}}

    # Возвращаем список кнопок, который будет использоваться в меню
    return [button_help, button_hello, button_art, button_translate, button_pass]
# Функция бота, которая вызывается каждый раз при получении новых обновлений
def bot(update):
    global level
    but_back = {'text': 'Назад', 'callback_data': {'cmd': '/back'}}
    but_main = {'text': 'На главную', 'callback_data': {'cmd': '/to main'}}
    if update['text'] == "Заполнить форму": level = '11'
    elif update['text'] == "Получить информацию": level = '12'
    elif update['text'] == "Yandex GPT":level = '13'
    elif update['text'] == "Что я могу?":level = '14'
    elif update['text'] == "Запланировать командировку":level = '111'
    elif update['text'] == "Запланировать отпуск":level = '112'
    elif update['text'] == "Справки HR":level = '113'
    elif update['text'] == "ItHelp": level = '121'
    elif update['text'] == "Расписание транспорта": level = '122'
    elif update['text'] == "Обучение": level = '123'
    elif update['text'] == "Корпоративный портал": level = '124'
    elif update['text'] == "Назад": level = level[0:len(level) - 1]
    elif update['text'] == "На главную": level = '1'
    else: level = '1'


    if level == '11':
        but_work = {'text': 'Запланировать командировку', 'callback_data': {'cmd': '/work'}}
        but_holiday = {'text': 'Запланировать отпуск', 'callback_data': {'cmd': '/holiday'}}
        but_hr = {'text': 'Справки HR', 'callback_data': {'cmd': '/hr'}}
        buttons = [but_work, but_holiday, but_hr, but_back]
        send_inline_keyboard('Формы', buttons, update)
    elif level == '12': 
        but_ithelp = {'text': 'ItHelp', 'callback_data': {'cmd': '/ithelp'}}
        but_schedule = {'text': 'Расписание транспорта', 'callback_data': {'cmd': '/schedule'}}
        but_education = {'text': 'Обучение', 'callback_data': {'cmd': '/education'}}
        but_wiki = {'text': 'Корпоративный портал', 'callback_data': {'cmd': '/wiki'}}
        buttons = [but_ithelp, but_schedule,but_education, but_wiki, but_back]
        send_inline_keyboard('Информация', buttons, update)
    
    elif level == '13':
        buttons = [but_back, but_main]
        send_inline_keyboard('В разработке', buttons, update)
    elif level == '14':
        buttons = [but_back, but_main]
        send_inline_keyboard('Скоро здесь будет информация о том,что я могу',buttons,  update)
# Заполнить форму
    elif level == '111':
        buttons = [but_back, but_main]
        send_inline_keyboard('Чтобы запланировать командировку, заполните форму: ''https://forms.yandex.ru/cloud/66b5c63df47e7304136e26f1/',buttons,  update)
    elif level == '112':
        buttons = [but_back, but_main]
        send_inline_keyboard('Чтобы запланировать отпуск, заполните форму: ''https://forms.yandex.ru/cloud/66b5c63df47e7304136e26f1/',buttons,  update)
    elif level == '113':
        buttons = [but_back, but_main]
        send_inline_keyboard('Чтобы получить справку от HR, заполните форму: ''https://forms.yandex.ru/cloud/66b5c63df47e7304136e26f1/',buttons,  update)

# Получить информацию
    elif level == '121':
        buttons = [but_back, but_main]
        send_inline_keyboard('Чтобы связаться со специалистом,напишите на почту или Яндекс Мессенджер: ''ithelp@sollers-auto.com',buttons,  update)
    elif level == '122':
        buttons = [but_back, but_main]
        send_inline_keyboard('Чтобы узнать расписание транспорта,перейдите по ссылке: ''https://t.me/+t7OWn8saTu0wZTdi',buttons,  update)
    elif level == '123':
        buttons = [but_back, but_main]
        send_inline_keyboard('https://wiki.yandex.ru/proekt-jandeks-360/jandeks-360-dlja-proektnojj-komandy/',buttons,  update)
    elif level == '124':
       buttons = [but_back, but_main]
       send_inline_keyboard('https://wiki.yandex.ru/elabuga/',buttons,  update)
#Главная
    elif level == '1':
        but_forms = {'text': 'Заполнить форму', 'callback_data': {'cmd': '/forms'}}
        but_info = {'text': 'Получить информацию', 'callback_data': {'cmd': '/info'}}
        but_gpt = {'text': 'Yandex GPT', 'callback_data': {'cmd': '/gpt'}}
        but_help = {'text': 'Что я могу?', 'callback_data': {'cmd': '/help'}}
        buttons = [but_forms, but_info, but_gpt, but_help]
        send_inline_keyboard('Доступные разделы:', buttons, update)

def send_text(request_body, update):
    if update['chat']['type'] == 'group':  # Если исходное сообщение отправлено в групповой чат, то отвечаем в него
        request_body.update({'chat_id': update['chat']['id']})

    elif update['chat']['type'] == 'private':  # Если сообщение отправлено персонально боту, то отвечаем лично
        request_body.update({'login': update['from']['login']})

    post(SEND_TEXT_URL, json=request_body, headers=yb)  # отправляем сообщение

def send_message(text, update):
    request_body = {'text': text}  # В тело запроса для отправки сообщения добавляем исходный текст сообшения
    send_text(request_body, update)

def send_inline_keyboard(text, button, update):
    request_body = {'text': text, 'inline_keyboard': button}
    return send_text(request_body, update)

def send_menu(update, menu):  # Отправляем пользователю инлайн-кнопки с текстом и кнопками из меню
    yb.send_inline_keyboard(text='Доступные команды:', buttons=menu, update=update)


if __name__ == "__main__":  # Проверяем, что этот файл исполняется как основной скрипт
    main_menu = build_menu() # Создаем главное меню, вызывая функцию build_menu()
    manager = multiprocessing.Manager() # Создаем менеджер для работы с многопоточностью
    art_queue = manager.dict() # Создаем словарь (или очередь) для передачи данных между процессами
    art_process = multiprocessing.Process(target=art_thread, args=(art_queue, main_menu)) # Запускаем новый процесс для генерации изображений

    print('Starting art thread...') # Сообщаем о запуске потока генерации изображений
    art_process.start() # Запускаем процесс
    yb.start_pooling()  #Начинаем опрос (polling) для получения обновлений от пользователя
