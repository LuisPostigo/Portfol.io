# exchanges.py
import pika

def declare_exchanges(channel):
    channel.exchange_declare(exchange='portfol_io.direct', exchange_type='direct', durable=True)
    channel.exchange_declare(exchange='portfol_io.topic', exchange_type='topic', durable=True)
