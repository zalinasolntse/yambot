import multiprocessing                                                                   # Импортируем модуль для работы с многопоточностью
import os                                                                                # Импортируем модуль для работы с операционной системой
from time import sleep                                                                   # Импортируем функцию sleep для паузы в выполнении

# Импортируем функцию для загрузки переменных окружения
from dotenv import load_dotenv 

# Импортируем функции из API
from api.gpt_api import send_translate_request, send_art_request, get_art_response
from api.tracker_api import create_ticket
from yambot.yambot import MessengerBot

# Загружаем переменные окружения из файла .env( В НЕМ НАХОДЯТСЯ ВСЕ ТОКЕНЫ И КЛЮЧИ API)
load_dotenv()
yb = MessengerBot(os.getenv('BOT_KEY'))                                                  # Создаем экземпляр бота с ключом из переменных окружения
main_menu = []                                                                           # Инициализируем основные структуры данных
translate_requests = {}                                                                  # Основное меню
pass_requests = {}                                                                       # Словарь для хранения запросов на перевод
art_requests = {}                                                                        # Словарь для хранения запросов на генерацию изображения
art_queue = {} 


@yb.add_handler(command='/debug')
def show_handlers(update):                                                               #Команда для отображения всех обработчиков.
    yb.list_handlers()


#@yb.add_handler(button='/translate')
#def translate_button(update):                                                            #Обработчик кнопки перевода. Запрашивает текст для перевода.
    #yb.send_message(f'Введите текст для перевода:', update)
    #translate_requests.update({f'{update.from_m.from_id}': update})                      # Сохраняем запрос

#КНОПКИ
#Кнопки "Полезная информация"
but_ithelp = {'text': 'IT Help', 'callback_data': {'cmd': '/ithelp'}}
but_car= {'text': 'Расписание транспорта', 'callback_data': {'cmd': '/car'}}
but_main={'text': 'Назад', 'callback_data': {'cmd': '/main'}}
but_help = [but_ithelp, but_car,but_main]

#Кнопки "Оформить пропуск"
but_work= {'text': 'Командировка', 'callback_data': {'cmd': '/work'}}
#but_ticket ={'text': 'Пропуск', 'callback_data': {'cmd': '/ticket'}}
but_holiday={'text': 'Отпуск', 'callback_data': {'cmd': '/holiday'}}
button_pass = {'text': 'Оформление пропусков', 'callback_data': {'cmd': '/pass'}}
but_zayavki=[but_work,but_holiday,button_pass,but_main]

#кнопки "YandexGPT"
button_art = {'text': '🏞️ Генерация изображения', 'callback_data': {'cmd': '/art'}}
button_text= {'text': '💬 Генерация текста', 'callback_data': {'cmd': '/text'}}
button_requests=[button_art,button_text,but_main]

#ФУНКЦИЯ КНОПОК
#полезная информация
@yb.add_handler(button='/info')
def info_button(update):  
    yb.send_inline_keyboard(text='`Полезная информация:`', buttons = but_help, update = update)                                                          #Обработчик кнопки перевода. Запрашивает текст для перевода.

@yb.add_handler(button='/ithelp')
def but_ithelp(update):  
    yb.send_message(f'Напишите сотруднику поддержки в [**Я. Мессенджере**](https://yandex.ru/chat#/user/c8677c02-b3cd-9a51-5fcb-bc5dff265fb0) или на почту: ithelp@sollers-auto.com',update)
    send_menu(update, but_help)

@yb.add_handler(button='/car')
def but_car(update):  
    yb.send_message(f'Вы можете присоединиться к нашей группе в [**Телеграм-канал**](https://t.me/+t7OWn8saTu0wZTdi) для получения оперативной информации.',update)
    send_menu(update, but_help)

@yb.add_handler(button='main')
def but_main(update):  
    send_menu(update, main_menu)

#оформить заявку
@yb.add_handler(button='/test')
def test_button(update):  
    yb.send_inline_keyboard(text='`Оформить заявку:`', buttons = but_zayavki, update = update)

@yb.add_handler(button='/work')
def but_work(update):  
    yb.send_message(f'Здесь скоро появится инструкция как оформить командировку',update)
    send_menu(update, but_zayavki)

#@yb.add_handler(button='/ticket')
#def but_ticket(update):  
    #yb.send_message(f'Здесь скоро появится инструкция как оформить пропуск',update)
    #send_menu(update, but_zayavki)

@yb.add_handler(button='/holiday')
def but_holiday(update):  
    yb.send_message(f'Здесь скоро появится инструкция как оформить отпуск',update)   
    send_menu(update, but_zayavki)


@yb.add_handler(button='/pass')
def pass_button(update):                                                                 #Обработчик кнопки пропуска. Запрашивает имя и фамилию для заказа пропуска.
    yb.send_message(f'`Введите имя и фамилию для заказа пропуска:`', update)
    pass_requests.update({f'{update.from_m.from_id}': update})                           # Сохраняем запрос

@yb.add_handler(button='/pass_yes')
def pass_yes(update):
    res = create_ticket(update.callback_data['name'])                                    #Обработчик подтверждения заказа пропуска.
    yb.send_message(f"`Заявка на пропуск оформлена:` https://tracker.yandex.ru/{res['key']}", update)
    send_menu(update, main_menu)                                                         # Возвращаем в основное меню

@yb.add_handler(button='/pass_no')
def pass_no(update):                                                                     #Обработчик отмены заказа пропуска.
    yb.send_message(f'"`Заказ пропуска отменен`', update)
    send_menu(update, main_menu)      


#кнопка назад
@yb.add_handler(button='/back')
def but_back(update):  
    send_menu(update, main_menu)

#кнопка YandexGPT
@yb.add_handler(button='/gpt')
def gpt_button(update):  
    yb.send_inline_keyboard(text='`Yandex GPT` ', buttons = button_requests, update = update)

@yb.add_handler(button='/text')
def but_text(update):  
    yb.send_message(f'Здесь скоро появится инструкция как cгенерировать текст',update)   
    send_menu(update, button_requests)

@yb.add_handler(button='/art')
def art_button(update):                                                                  #Обработчик кнопки генерации изображения. Запрашивает текст для генерации.
    yb.send_message(f'`Введите текст для генерации изображения:`', update)
    art_requests.update({f'{update.from_m.from_id}': update})                            # Сохраняем запрос


@yb.add_handler(button='/art_yes')
def art_yes(update):                                                                     #Обработчик подтверждения генерации изображения.
    response = send_art_request(update.callback_data['text'])                            # Отправляем запрос на генерацию изображения
    print(f"Art response: {response}")
    try:
        yb.send_message(f"`Запрос на генерацию изображения отправлен.`", update)
        art_queue.update({f"{response['id']}": update})                                  # Сохраняем запрос в очередь
    except KeyError:
        yb.send_message(f"Ошибка: {response['error']}", update)                          # Обработка ошибки
        send_menu(update, main_menu)                                                     # Возвращаем в основное меню

@yb.add_handler(button='/art_no') 
def art_no(update):                                                                      # Обработчик отмены генерации изображения
    yb.send_message(f'"`Генерация изображения отменена`', update)
    send_menu(update, main_menu) # Возвращаем в основное меню


@yb.add_handler(any=True)
def process_any(update):                                                                 # Обработчик всех других сообщений.
    if f'{update.from_m.from_id}' in translate_requests:
        response = send_translate_request(update.text)                                   # Отправляем текст на перевод
        text = response['translations'][0]['text']                                       # Получаем перевод
        yb.send_message(f"Перевод:\n```{text}```", update)                               # Отправляем перевод пользователю
        translate_requests.pop(f'{update.from_m.from_id}', None)                         # Удаляем запрос
        send_menu(update, main_menu)
    elif f'{update.from_m.from_id}' in pass_requests:                                    # Создаем кнопки для подтверждения или отмены заказа пропуска
        button_pass_yes = {'text': '✔️Да', 'callback_data': {'cmd': '/pass_yes', 'name': update.text}}
        button_pass_no = {'text': '❌Нет', 'callback_data': {'cmd': '/pass_no'}}
        yb.send_inline_keyboard(
            f'Заказать пропуск для: {update.text}?',
            [button_pass_yes, button_pass_no],
            update
        )
        pass_requests.pop(f'{update.from_m.from_id}', None)                               # Удаляем запрос
    elif f'{update.from_m.from_id}' in art_requests:                                      # Создаем кнопки для подтверждения или отмены генерации изображения
        button_art_yes = {'text': '✔️Да', 'callback_data': {'cmd': '/art_yes', 'text': update.text}}
        button_art_no = {'text': '❌Нет', 'callback_data': {'cmd': '/art_no'}}
        yb.send_inline_keyboard(
            f'`Сгенерировать изображение по запросу: {update.text}?`',
            [button_art_yes, button_art_no],
            update
        )
        art_requests.pop(f'{update.from_m.from_id}', None)                                # Удаляем запрос
    else:
        send_menu(update, main_menu)                                                      # Если нет активных запросов, возвращаем в меню


def art_thread(art_q, menu):                                                              # Фоновый поток для обработки очереди генерации изображений.
    #  global art_queue
    while True:
        print("Art queue size: ", len(art_q))                                             # Выводим размер очереди
        for art_request in art_q.keys():
            response = get_art_response(art_request)                                      # Получаем ответ о готовности изображения
            if response['done']:
                yb.send_message("`Изображение готово`", art_q[art_request])                 # Уведомляем пользователя
                yb.send_image(response['response']['image'], art_q[art_request])          # Отправляем изображение
                send_menu(art_q[art_request], menu)                                       # Возвращаем в меню
                art_q.pop(art_request, None)                                              # Удаляем обработанный запрос
                break
            
            # Если условие в предыдущем блоке не выполнено, выполняем этот код
            else:
                print(art_q)                                                              # Выводим содержимое очереди art_q в консоль для отладки
                                                                                          # Отправляем сообщение пользователю о том, что идет процесс генерации
                yb.send_message("`Генерируется...`", art_q[art_request])
        # print("Sleeping")
        sleep(10)                                                                         # Приостанавливаем выполнение на 10 секунд


def build_menu(): # Создаем кнопки для меню с текстом и соответствующими командами
    #button_help = {'text': 'Главное меню 🏠', 'callback_data': {'cmd': '/help'}}
    button_test = {'text': '📋 Оформить заявку', 'callback_data': {'cmd': '/test'}}
    button_info = {'text': '📕 Полезная информация', 'callback_data': {'cmd': '/info'}}
    button_gpt = {'text': '👽 Yandex GPT ', 'callback_data': {'cmd': '/gpt'}}
    #button_translate = {'text': 'Перевод', 'callback_data': {'cmd': '/translate'}}
    

    # Возвращаем список кнопок, который будет использоваться в меню
    return [button_test, button_info,button_gpt]

def send_menu(update, menu):  # Отправляем пользователю инлайн-кнопки с текстом и кнопками из меню
    yb.send_inline_keyboard(text='`Доступные команды:`', buttons=menu, update=update)

if __name__ == "__main__":  # Проверяем, что этот файл исполняется как основной скрипт
    main_menu = build_menu() # Создаем главное меню, вызывая функцию build_menu()
    manager = multiprocessing.Manager() # Создаем менеджер для работы с многопоточностью
    art_queue = manager.dict() # Создаем словарь (или очередь) для передачи данных между процессами
    art_process = multiprocessing.Process(target=art_thread, args=(art_queue, main_menu)) # Запускаем новый процесс для генерации изображений

    print('Starting art thread...') # Сообщаем о запуске потока генерации изображений
    art_process.start() # Запускаем процесс
    yb.start_pooling()  #Начинаем опрос (polling) для получения обновлений от пользователя