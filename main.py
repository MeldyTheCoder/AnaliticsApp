import flet as ft
from flet.matplotlib_chart import MatplotlibChart
from files import FileManager
from database import ChartHistory

FILE_MANAGER = FileManager()

KEYBOARD_TYPES = {
    int: ft.KeyboardType.NUMBER,
    str: ft.KeyboardType.TEXT
}


class AnalyticsApp:
    def __init__(self, page: ft.Page):
        self.chart_generated = False
        self.file_path = None

        self.page = page

        self.page.title = self.__class__.__name__
        self.page.theme_mode = 'dark'
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.file_picker = ft.FilePicker(on_result=self._open_file_result)

        self.page.overlay.append(self.file_picker)
        self.main_activity()

    def main_activity(self, *args, **kwargs):
        self.page.clean()

        self.file_path = None
        self.chart_generated = False

        self.page.add(
            ft.Row(
                [

                    ft.ElevatedButton(text='Открыть файл', icon=ft.icons.UPLOAD_FILE, on_click=self._open_file),
                    ft.OutlinedButton(text='Подключение к СУБД', icon=ft.icons.SAVE,
                                      on_click=self.database_load_activity),
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),

            ft.Row(
                [
                    ft.ElevatedButton(
                        text='История графиков',
                        icon=ft.icons.HISTORY,
                        on_click=self.chart_history_view_activity
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),

            ft.Row(
                [
                    ft.OutlinedButton(
                        text='Выход',
                        icon=ft.icons.EXIT_TO_APP,
                        on_click=self._exit_callback,
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER
            )
        )

    def database_load_activity(self, *args, **kwargs):
        self.page.clean()

        self.file_path = None

        database = kwargs.get('database')
        if not database:
            allowed_databases = FILE_MANAGER._database_readers

            database_selection = ft.RadioGroup(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Radio(label=cls.verbose_name, value=extension) for extension, cls in
                                allowed_databases.items()
                            ]
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            )

            self.page.add(
                database_selection,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            text='Назад',
                            icon=ft.icons.ARROW_BACK,
                            on_click=lambda *args, **kwargs: self.main_activity()
                        ),
                        ft.ElevatedButton(
                            text='Продолжить',
                            icon=ft.icons.NAVIGATE_NEXT,
                            on_click=lambda *args, **kwargs: self.database_load_activity(database=database_selection.value)
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                )
            )
            return

        self.file_path = database
        return self.field_input_activity(file_path=self.file_path)

    def handle_exception(self, exc):
        return self._show_dialog(str(exc))

    def _exit_callback(self, *args, **kwargs):
        self.page.window_destroy()

    def field_input_activity(self, *args, **kwargs):
        file_path = kwargs.get('file_path', self.file_path)

        assert file_path, 'Файл не выбран!'

        text_boxes = kwargs.get('text_boxes') or {}
        if text_boxes:
            field_data = {}

            for field, text_box in text_boxes.items():
                field_data[field] = text_box.value

            try:
                FILE_MANAGER.fields = field_data
                ChartHistory.create(file_name=file_path, extra_data=FILE_MANAGER.fields)
                return self.chart_view_activity(validated_data=FILE_MANAGER.fields)
            except Exception as e:
                self._show_dialog(str(e))

        required_fields, verbose_names = FILE_MANAGER.get_required_fields(file_path=self.file_path)
        if not required_fields:
            ChartHistory.create(file_name=file_path)
            return self.chart_view_activity()

        for required_field, data_type in required_fields.items():
            text_boxes[required_field] = ft.TextField(
                label=verbose_names[required_field],
                keyboard_type=KEYBOARD_TYPES.get(data_type, ft.KeyboardType.TEXT),
                on_change=None
            )

        self.page.clean()

        for text_box in text_boxes.values():
            self.page.add(
                ft.Row(
                    [
                        text_box
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                )
            )

        self.page.add(
            ft.Row(
                [
                    ft.ElevatedButton(
                        text='Продолжить',
                        icon=ft.icons.NAVIGATE_NEXT,
                        on_click=lambda *args, **kwargs: self.field_input_activity(text_boxes=text_boxes)
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER
            )
        )

        self.page.update()

    def chart_history_view_activity(self, *args, **kwargs):
        self.page.clean()

        self.file_path = None

        chart_id = kwargs.get('chart_id')
        if not chart_id:
            charts = ChartHistory.get_all_charts()

            list_view = ft.ListView(
                expand=1,
                spacing=10,
                padding=20,
                auto_scroll=True
            )

            for chart in charts:
                list_view.controls.append(
                    ft.ElevatedButton(
                        text=FILE_MANAGER.file_name(chart.file_name, data=chart.extra_data),
                        on_click=lambda e, chart_data=chart: self.chart_history_view_activity(chart_id=chart_data.id)
                    )
                )

            self.page.add(
                ft.OutlinedButton(
                    text='Назад',
                    icon=ft.icons.ARROW_BACK,
                    on_click=self.main_activity
                ),
                ft.Row(
                    [
                        list_view
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
            )
            return

        print(chart_id)
        chart = ChartHistory.get_chart(chart_id=chart_id)
        extra_data = chart.extra_data or {}

        self.file_path = chart.file_name

        return self.chart_view_activity(validated_data=extra_data)

    def chart_view_activity(self, *args, **kwargs):
        validated_data = kwargs.get('validated_data')

        try:
            assert self.file_path, 'Файл не выбран!'
            assert validated_data, 'Данные не указаны.'

            self.page.clean()

            self.page.add(
                ft.Row(
                    [
                        ft.ElevatedButton(text='Назад', icon=ft.icons.ARROW_BACK, on_click=self.main_activity)
                    ]
                )
            )

            chart = FILE_MANAGER.generate_chart(file_path=self.file_path, **validated_data)

            self.page.add(
                MatplotlibChart(chart, expand=True)
            )

            self.chart_generated = True
        except Exception as e:
            return self._show_dialog(str(e))

    def database_connect_activity(self, *args, **kwargs):
        self.page.clean()

    def _open_file_result(self, e, *args, **kwargs):
        self.file_path = e.files[0].path
        return self.field_input_activity()

    def _open_file(self, *args, **kwargs):
        self.file_picker.pick_files(
            dialog_title='Открыть файлы.',
            allowed_extensions=FILE_MANAGER.allowed_extensions,
            allow_multiple=False
        )

    def _show_dialog(self, message: str = None, critical_error: bool = False):
        if critical_error:
            return self.page.error(message)

        dialog = ft.AlertDialog(
            title=ft.Text(message, color='red'),
        )

        self.page.show_dialog(dialog)
        self.page.update()


if __name__ == '__main__':
    ft.app(target=AnalyticsApp)

