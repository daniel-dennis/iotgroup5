from flask import Flask
from flask import request
from flask import render_template
from flask import jsonify
import pymysql
import creds

import numpy as np

from datetime import datetime
app = Flask(__name__)

def get_weather(lon=53.0, lat=-6.0):
    """
        returns list of temperature forcast in 3 hour increments in degrees kelvin
    """
    import json, requests

    url = 'http://api.openweathermap.org/data/2.5/forecast?lat=%f&lon=%f&appid=622088a3351f45b5fd90814bf5b58670' % (lat, lon)
    data = requests.get(url=url)
    binary = data.content
    data = json.loads(binary)['list']
    temperature = []
    rain = []
    for datum in data:
        temperature.append(datum['main']['temp'])
        try:
            rain.append(datum['rain']['3h'])
        except KeyError:
            rain.append(0.0)

    return jsonify({
        'temperature': temperature,
        'rain': rain
    })

def post_to_db(temp, humidity, time=str(datetime.now()), greenhouse_id=1):
    connection = connect_db()
    try:
        sql = 'INSERT INTO `greenhouse_logs` VALUES(%s,%s,%s,%s);'
        sql_params = [greenhouse_id, temp, humidity, time]
        with connection.cursor() as cursor:
            cursor.execute(sql, sql_params)
        connection.commit()
    finally:
        connection.close()

def get_from_db(entry_limit=-1):
    '''
    entries: selects the most recent _entries_ records, if less than 1, then all records are returned
    '''
    assert(isinstance(entry_limit, int))
    connection = connect_db()
    try:
        if entry_limit > 0:
            sql = 'SELECT * FROM `greenhouse_logs` ORDER BY `time` DESC LIMIT %s;'
            sql_params = [entry_limit]
        else:
            sql = 'SELECT * FROM `greenhouse_logs`;'
            sql_params = []
        with connection.cursor() as cursor:
            cursor.execute(sql, sql_params)
            results = cursor.fetchall()
    finally:
        connection.close()
    return results

def connect_db():
    return pymysql.connect(
        host=creds.host,
        port=creds.port,
        password=creds.password,
        db=creds.db,
        user=creds.user
    )

@app.route("/")
def hello():
    # return "<h1> HOME <h1>" + str(type(get_from_db()))
    data = get_from_db(100)
    return render_template('index.html', greenhouse_data=data, greenhouse_len=len(data))

@app.route('/push', methods=['POST'])
def url_push():
    data = request.get_json(force=True)
    greenhouse_id = data['greenhouse_id']
    temp = data['temp']
    humidity = data['humidity']
    time = data['time']
    time = [int(i) for i in time.split(':')]
    time = datetime(time[0], time[1], time[2], time[3], time[4], time[5])
    post_to_db(temp, humidity, greenhouse_id=greenhouse_id, time=time.isoformat())
    return 'OK', 200

@app.route('/get_weather', methods=['GET'])
def get_weather_api():
    args = request.args
    try:
        lat = float(args['latitude'])
        lon = float(args['longitude'])
    except:
        lat = 53.0
        lon = -6.0
    
    return get_weather(lon=lon, lat=lat), 200

if __name__ == "__main__":
    app.run()
