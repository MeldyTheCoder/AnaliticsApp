import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from database import create_engine


def validate_required_fields(required_fields: dict, provided_fields: dict):
    if not required_fields:
        return

    assert provided_fields, \
        'Параметры для инициализации ридер-класса не указаны.' \
        f'Укажите параметры: {required_fields}'

    extra_kwargs_keys = set(provided_fields.keys())
    required_fields_keys = set(required_fields.keys())

    assert not required_fields_keys.difference(extra_kwargs_keys), \
        f'Недостаточно параметров для инициализации ридер-класса.' \
        f'Укажите параметры: {required_fields_keys.difference(extra_kwargs_keys)}'

    for field in list(extra_kwargs_keys):
        field_type = type(provided_fields[field])
        required_field_type = required_fields[field]

        if not provided_fields[field]:
            raise ValueError(
                f'Значение поля {field} не указано.'
            )

        if field_type != required_field_type:
            raise TypeError(
                f'Указан неверный тип данных для поля "{field}".'
                f'Должен быть "{required_field_type}" вместо "{field_type}".'
            )


class BaseReader:
    allowed_extension = None
    required_fields = {}
    required_fields_verbose_names = {}
    is_remote = False
    verbose_name = 'BaseReader'

    def __init__(self, file_path: str, no_validate: bool = False, **kwargs):
        self.file_path = file_path
        self.extra_kwargs = kwargs
        self.validate_file_path()

        self.no_validate = no_validate
        if not no_validate:
            self.validate_required_fields()

    def validate_required_fields(self):
        return validate_required_fields(
            required_fields=self.required_fields,
            provided_fields=self.extra_kwargs
        )

    def validate_file_path(self):
        raise NotImplemented('Данный метод не переопределен.')

    def read(self):
        raise NotImplemented('Данный метод не переопределен')

    def handle_exception(self, exc):
        raise exc


class BaseRemoteDatabaseReader(BaseReader):
    required_fields = {
        'table_name': str,
        'hostname': str,
        'port': str,
        'user': str,
        'password': str,
        'schema': str
    }

    required_fields_verbose_names = {
        'table_name': 'Название таблицы',
        'hostname': 'Хост',
        'port': 'Порт',
        'user': 'Пользователь',
        'password': 'Пароль',
        'schema': 'База данных'
    }

    is_remote = True

    def validate_file_path(self):
        assert self.allowed_extension, f'Расширение для "{self.__class__.__name__}" не было указано.'

    def read(self):
        table_name = self.extra_kwargs.get('table_name')
        hostname = self.extra_kwargs.get('hostname')
        port = self.extra_kwargs.get('port')
        user = self.extra_kwargs.get('user')
        password = self.extra_kwargs.get('password')
        schema = self.extra_kwargs.get('schema')

        engine = create_engine(
            f'{self.allowed_extension}://{user}:{password}@{hostname}:{port}/{schema}'
        )

        dataframe = pd.read_sql_table(
            table_name=table_name,
            con=engine,
            coerce_float=True
        )

        dataframe.select_dtypes(include=np.number)
        return dataframe

    def __str__(self):
        hostname = self.extra_kwargs.get('hostname', '???')
        table_name = self.extra_kwargs.get('table_name', '???')

        return f"{self.verbose_name} | {hostname}/{table_name}"


class BaseFileReader(BaseReader):
    def validate_file_path(self):
        assert self.allowed_extension, f'Расширение для "{self.__class__.__name__}" не было указано.'
        assert self.file_path.endswith(self.allowed_extension), \
            f'Расширение "{self.allowed_extension}" не поддерживается' \
            f'ридер-классом "{self.__class__.__name__}".'

    def __str__(self):
        return f"{self.verbose_name} | {self.file_path}"


class CsvReader(BaseFileReader):
    allowed_extension = 'csv'
    verbose_name = 'CSV'

    def read(self):
        dataframe = pd.read_csv(filepath_or_buffer=self.file_path)
        dataframe.select_dtypes(include=np.number)
        return dataframe


class JsonReader(BaseFileReader):
    allowed_extension = 'json'
    verbose_name = 'JSON'

    def read(self):
        dataframe = pd.read_json(path_or_buf=self.file_path)
        dataframe.select_dtypes(include=np.number)
        print(dataframe)
        return dataframe


class PickleReader(BaseFileReader):
    allowed_extension = 'pickle'
    verbose_name = 'Pickle'

    def read(self):
        dataframe = pd.read_pickle(filepath_or_buffer=self.file_path)
        dataframe.select_dtypes(include=np.number)
        return dataframe


class HtmlReader(BaseFileReader):
    allowed_extension = 'html'
    verbose_name = 'HTML'

    def read(self):
        dataframe = pd.read_html(io=self.file_path)
        return dataframe


class XmlReader(BaseFileReader):
    allowed_extension = 'xml'
    verbose_name = 'XML'

    def read(self):
        dataframe = pd.read_xml(path_or_buffer=self.file_path)
        dataframe.select_dtypes(include=np.number)


class SqliteReader(BaseFileReader):
    allowed_extension = 'db'
    verbose_name = 'SQLite'

    required_fields = {
        'table_name': str
    }

    required_fields_verbose_names = {
        'table_name': 'Название таблицы'
    }

    def read(self):
        table_name = self.extra_kwargs.get('table_name')
        engine = create_engine('sqlite:///' + self.file_path)

        dataframe = pd.read_sql_table(
            table_name=table_name,
            con=engine,
            coerce_float=True
        )

        dataframe.select_dtypes(include=np.number)
        return dataframe


class MySQLReader(BaseRemoteDatabaseReader):
    allowed_extension = 'mysql+pymysql'
    verbose_name = 'MySQL'


class PostgreSQlReader(BaseRemoteDatabaseReader):
    allowed_extension = 'postgresql+psycopg2'
    verbose_name = 'PostgreSQL'


class MariaDBReader(BaseRemoteDatabaseReader):
    allowed_extension = 'mariadb+pymysql'
    verbose_name = 'MariaDB'


class FileManager:
    _extension_readers: dict = {
        cls.allowed_extension: cls for cls in BaseFileReader.__subclasses__()
    }

    _database_readers: dict = {
        cls.allowed_extension: cls for cls in BaseRemoteDatabaseReader.__subclasses__()
    }

    allowed_extensions = list(_extension_readers.keys())

    required_fields = {
        'plot_verbose': str,
        'plot_value': str
    }

    required_fields_verbose_names = {
        'plot_verbose': 'Поле обозначения координат',
        'plot_value': 'Поле координат'
    }

    def __init__(self):
        self.__extra_kwargs = {}
        self.__current_file_path = None

    @property
    def fields(self):
        return self.__extra_kwargs

    @fields.setter
    def fields(self, value: dict):
        self.__extra_kwargs = value.copy()
        self._validate_required_fields()

    def _validate_required_fields(self):
        return validate_required_fields(
            required_fields=self.get_required_fields(self.__current_file_path)[0],
            provided_fields=self.fields
        )

    def _validate_file(self, file_path: str):
        if file_path in self._database_readers:
            return file_path

        assert '.' in file_path, 'Неизвестное расширение файла.'
        extension = file_path.split('.')[-1]

        assert extension in self.allowed_extensions, \
            'Данного расширения нет в списке разрешенных.'\
            f'Доступные расширения: {", ".join(self.allowed_extensions)}'

        assert extension in self._extension_readers, \
            'Данное расширение не поддерживается.' \
            f'Поддерживаемые расширения: {", ".join(self._extension_readers.keys())}'

        return extension

    def _get_file_reader_class(self, extension):
        reader_class = self._extension_readers.get(extension) or self._database_readers.get(extension)

        assert reader_class, 'Ридер-класс не был найден!'

        return reader_class

    def file_name(self, file_path: str, data: dict = None):
        extension = self._validate_file(file_path)
        reader_class = self._get_file_reader_class(extension)
        reader_instance = reader_class(file_path=file_path, no_validate=True, **data)

        reader_str = str(reader_instance)

        del reader_instance
        return reader_str

    def _open_file(self, file_path: str, *args, **kwargs):
        extension = self._validate_file(file_path)
        reader_class = self._get_file_reader_class(extension)
        return reader_class(file_path, *args, **kwargs).read()

    def get_required_fields(self, file_path: str):
        self.__current_file_path = file_path

        extension = self._validate_file(file_path)
        reader_class = self._get_file_reader_class(extension)

        required_fields = reader_class.required_fields.copy()
        required_fields.update(self.required_fields)

        required_fields_verbose_names = reader_class.required_fields_verbose_names.copy()
        required_fields_verbose_names.update(self.required_fields_verbose_names)

        return (
            required_fields,
            required_fields_verbose_names
        )

    def generate_chart(self, file_path: str, *args, **kwargs):
        plot_verbose = kwargs.pop('plot_verbose')
        plot_value = kwargs.pop('plot_value')

        file = self._open_file(file_path, *args, **kwargs)
        self.__current_file_path = None

        figure, ax = plt.subplots()
        values = (plot_verbose, plot_value)
        ax.plot(*[file[key] for key in values[0:2]])
        return figure

