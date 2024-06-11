[К содержанию](../readme.md)

## Инструкция по развертыванию Docker и базовым командам

----

### Развертывание Docker

* Перейдите в корневую папку проекта через `терминал`.
    * При первоначальном запуске нужно выполнить команду ````docker-compose build````, для того чтобы конфиг развернул все зависимости и установил пакеты, а также собрал образы и контейнеры. Дальше эта комманда не потребуется.
    * Запускаем контейнеры, без установки зависимостей - ````docker-compose up -d````.
    * Чтобы остановить контейнеры, используйте команду - ```docker-compose down```.
    * Чтобы перезапустить контейнеры, используйте команду - ```docker-compose restart```.

### Основные команды Docker:

* Запуск образа:

   ```bash
   # daemon режим
   docker run ubuntu -d
   # интерактивный режим (запускаем bash)
   docker run -it ubuntu bash
   ```

* Cписок образов, которые нам доступны в локальном репозитории:
   ```bash
   docker images
   ```

* Список контейнеров
   * Запущенные:
   
      ```bash
      docker ps
      ```
   * Все:
   
      ```bash
      docker ps -a
      # Получить список id контейнеров
      docker ps -aq
      ```

* Запуск, остановка контейнера:

   ```bash
   docker start containername
   docker stop containername
   ```
* Получение информация о контейнере
   * Общая информация:
   
      ```bash
      docker inspect containername
      ```

   * Дифы от начального состояния:
   
      ```bash
      docker diff containername
      ```
   * Лог контейнера:
   
      ```bash
      docker logs containername
      ```

* Удаление контейнеров:

   ```bash
   docker rm -v $(docker ps -aq) # Все
   docker rm -v $(docker ps -q) # Все активные
   docker rm -v $(docker ps -aq -f status=exited) # Все неактивные
   ```

* Удаляем "висячие образы":

   ```
   docker rmi $(docker images -f "dangling=true" -q)
   ```
* Удалить любой из образов по id:
   
   ```
   docker rmi container_name
   ```
* Зайти в контейнер с хостовой машины:
   
   ```
   docker exec -ti container_name /bin/bash
   ```
* Провести очистку системы: 
   
   ```
   docker system prune
   ```
   
### Основные команды Docker-Compose:

* Создаем контейнер:

   ```
   docker-compose up -d
   ```

* Остановка и удаление контейнеров:

   ```
   docker-compose down
   ```
* Перезапуск контейнеров: 

   ```
   docker-compose restart
   ```   

* Выполняем команду в контейнере:

   ```
   docker exec -it container_name bash
   ```
[Следующий шаг: Базовая информация по приложению](./basicInfo.md)