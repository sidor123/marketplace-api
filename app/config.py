import os


def required(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise RuntimeError(f'{name} must be set in the environment')
    return value


def database_url():
    value = required('DATABASE_URL')
    if value.startswith('postgresql://'):
        value = value.replace('postgresql://', 'postgresql+psycopg://', 1)
    if not value.startswith('postgresql+psycopg://'):
        raise RuntimeError('DATABASE_URL must use PostgreSQL (postgresql://)')
    return value


def positive_int(name, default):
    value = int(os.environ.get(name, default))
    if value < 1:
        raise RuntimeError(f'{name} must be positive')
    return value
