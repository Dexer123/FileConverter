from proglog import ProgressBarLogger
from PIL import Image
import moviepy.editor as moviepy
import flet as ft
import os
 
 
 
def generate_unique_filename(base_path, extension):
        counter = 1
        unique_path = f"{base_path}.{extension}"
        while os.path.exists(unique_path):
            unique_path = f"{base_path} ({counter}).{extension}"
            counter += 1
        return unique_path 


class snack():
    def __init__(self, text: str, page: ft.Page):
        snack_bar = ft.SnackBar(ft.Text(text))
        page.overlay.append(snack_bar)
        snack_bar.open = True 


class LabelTitle(ft.Container):
    def __init__(self, text: str):
        super().__init__()
        self.content=ft.Text(text, size=30)
        self.padding=ft.padding.Padding(200,10,10,10)


class FilePicker(ft.Row):
    def __init__(self, page: ft.Page, file_type: ft.FilePickerFileType):
        super().__init__()
        self.page = page
        self.type = file_type
        self.selected_files = None
        self.pick_files_dialog = ft.FilePicker(on_result=self.pick_files_result)
        self.page.overlay.append(self.pick_files_dialog)
        self.selected_files_text = ft.Text('Files: ', width=500, max_lines=4)
        
        self.controls = [
            ft.ElevatedButton('Select files', icon=ft.icons.FILE_UPLOAD, on_click=self.pick_files_click),
            self.selected_files_text
        ]
        
    def pick_files_click(self, event):
        self.pick_files_dialog.pick_files(allow_multiple=True, file_type=self.type)

    def pick_files_result(self, event: ft.FilePickerResultEvent):
        if event.files:
            self.selected_files_text.value = 'Files: ' + ', '.join([f.name + self.format_bytes(f.size) for f in event.files])
            self.selected_files = event.files
        else:
            self.selected_files_text.value = 'Cancelled!'
        self.selected_files_text.update()

    def format_bytes(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f" - {size:.2f} {unit}"
            size /= 1024


class CustomBarLogger(ProgressBarLogger):
    def __init__(self, page: ft.Page, progress_bar: ft.ProgressBar, progress_label: ft.Text, file_name: str):
        super().__init__()
        self.page = page
        self.file_name = file_name
        self.progress_bar = progress_bar
        self.progress_label = progress_label

    def callback(self, **changes):
        bars = self.state.get('bars', {})
        for bar_name, bar_data in bars.items():
            index = bar_data.get('index', 0)
            total = bar_data.get('total', 1)
            percentage = max(0, min(1, index / total if total > 0 else 0))  # Ensure percentage is between 0 and 1
            if not (bar_name == 'chunk' and percentage == 1):
                self.progress_bar.value = percentage
                self.progress_label.value = f"Converting {self.file_name + ('Audio' if bar_name == 'chunk' else 'Video')}: {percentage*100:.2f}%"
            self.page.update()

    def bars_callback(self, bar, attr, value, old_value):
        self.callback()


class VideoConverter(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.create_elements()
        self.setup_layout()

    def create_elements(self):
        self.convert_label = ft.Text('Convert to: ', style=ft.TextStyle(size=22))
        self.format_dd = self.create_format_dropdown()
        self.codec_dd = self.create_codec_dropdown()
        self.fps_dd = self.create_fps_dropdown()
        self.user_fps = self.create_user_fps_textfield()
        self.audio_switch = self.create_audio_switch()
        self.progress_bar_overall_label = ft.Text(value="Overall Progress", visible=False)
        self.progress_bar_overall = self.create_progress_bar(label="Overall Progress")
        self.progress_bar_file_label = ft.Text(value="", visible=False)
        self.progress_bar_file = self.create_progress_bar(label="File Progress")
        self.file_picker = FilePicker(self.page, ft.FilePickerFileType.VIDEO)
        self.convert_button = ft.ElevatedButton('Convert', icon=ft.icons.TASK_ALT, on_click=self.convert, disabled=True)

    def setup_layout(self):
        format_row = ft.Row([
            self.convert_label,
            self.format_dd,
            self.codec_dd
        ])

        fps_row = ft.Row([
            self.fps_dd,
            self.user_fps,
            self.audio_switch
        ])
        
        convert_row = ft.Row([
            self.convert_button
        ])

        title_label = LabelTitle('Video files converter')

        self.controls = [title_label, self.file_picker, format_row, fps_row, convert_row, self.progress_bar_overall_label, self.progress_bar_overall, self.progress_bar_file_label, self.progress_bar_file]

    def create_format_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            width=150,
            label='Format',
            border_radius=10,
            options=[ft.dropdown.Option(fmt) for fmt in ['mp4', 'avi', 'webm', 'mkv', 'mov', 'flv', 'ts', 'ogv', '3gp', 'gif', 'wav', 'mp3', 'aac', 'm4a', 'ogg', 'flac', 'opus']],
            padding=15,
            on_change=self.dd_codec
        )


    def create_codec_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            width=250,
            label='Codec',
            border_radius=10,
            options=[ft.dropdown.Option('-')],
            padding=15
        )

    def create_fps_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            width=100,
            label='Fps',
            border_radius=10,
            padding=15,
            value='Auto',
            on_change=self.dd_fps,
            options=[ft.dropdown.Option(fps) for fps in ['Auto', '15', '30', '60', '120', 'Your']]
        )

    def create_user_fps_textfield(self) -> ft.TextField:
        return ft.TextField(
            label='Fps: ',
            width=100,
            max_lines=1,
            visible=False
        )

    def create_audio_switch(self) -> ft.Switch:
        return ft.Switch(
            label='  Audio',
            label_style=ft.TextStyle(size=22),
            value=True,
            scale=0.8
        )

    def create_progress_bar(self, label: str) -> ft.ProgressBar:
        return ft.ProgressBar(width=500, height=8, visible=False, tooltip=label)

    def dd_codec(self, event):
        format_codecs = {
            # Video
            'mp4': ['libx264', 'libx265', 'mpeg4'],
            'avi': ['libx264', 'libxvid', 'png', 'rawvideo'],
            'webm': ['libvpx', 'libvpx-vp9', 'libvorbis'],
            'mkv': ['libx264', 'libx265', 'vp8', 'vp9', 'mpeg4'],
            'mov': ['libx264', 'mpeg4', 'prores'],
            'flv': ['libx264', 'flv1'],
            'ts': ['libx264', 'h264', 'mpeg2video'],
            'ogv': ['libtheora', 'libvorbis'],
            '3gp': ['mpeg4', 'h263'],
            'gif': ['gif'],
            # Audio
            'wav': ['pcm_s16le'],
            'mp3': ['libmp3lame'],
            'aac': ['aac', 'libfdk_aac'],
            'm4a': ['libfdk_aac'],
            'ogg': ['libvorbis'],
            'flac': ['flac'],
            'opus': ['libopus']
        }
        self.format_selected = self.format_dd.value
        codecs = format_codecs.get(self.format_selected, ['-'])
        self.codec_dd.options = [ft.dropdown.Option(codec) for codec in codecs]
        self.codec_dd.value = codecs[0]
        if self.format_selected:
            self.convert_button.disabled = False
        if self.format_selected in ['wav', 'mp3', 'aac', 'm4a', 'ogg', 'flac', 'opus']: # if audio
            self.fps_dd.visible = False
            self.audio_switch.visible = False
        else: 
            self.fps_dd.visible = True
            self.audio_switch.visible = True
        self.page.update()

    def dd_fps(self, event):
        self.user_fps.visible = self.fps_dd.value == 'Your'
        self.page.update()

    def convert(self, event):
        files = self.file_picker.selected_files
        if files:
            successful = True
            total_files = len(files)
            codec_selected = self.codec_dd.value
            fps_selected = self.user_fps.value if self.fps_dd.value == 'Your' else self.fps_dd.value
            fps_selected = None if fps_selected == 'Auto' else int(fps_selected)
            audio = self.audio_switch.value

            self.progress_bar_overall_label.visible = True
            self.progress_bar_overall.visible = True
            self.progress_bar_file_label.visible = True
            self.progress_bar_file.visible = True
            self.progress_bar_overall.value = 0
            self.page.update()

            for index, file in enumerate(files):
                try:
                    clip = moviepy.VideoFileClip(file.path)
                    base_path = '.'.join(file.path.split('.')[:-1])
                    output_path = generate_unique_filename(base_path, self.format_selected)
                    self.filename = output_path.split('\\')[-1]+' '

                    self.progress_bar_file_label.value = f"Converting {self.filename}"
                    self.page.update()

                    logger = CustomBarLogger(self.page, self.progress_bar_file, self.progress_bar_file_label, self.filename)
                    if self.format_selected not in ['wav', 'mp3', 'aac', 'm4a', 'ogg', 'flac', 'opus']: # if not audio
                        clip.write_videofile(
                            output_path,
                            codec=codec_selected,
                            fps=fps_selected,
                            audio=audio,
                            logger=logger
                        )
                    else:
                        clip.audio.write_audiofile(output_path, codec=codec_selected, logger=logger)
                except Exception as e:
                    print(f"Error converting file {file.path}: {e}")
                    snack(f"Error converting file {file.path}: {e}", self.page)
                    successful = False
                finally:
                    self.progress_bar_overall_label.value = f'Overall Progress {index + 1}/{total_files}'
                    self.progress_bar_overall.value = (index + 1) / total_files
                    self.page.update()

            
            self.progress_bar_overall_label.value = 'Overall Progress'
            for bar in [self.progress_bar_overall_label,  self.progress_bar_overall,  
                        self.progress_bar_file_label, self.progress_bar_file]:
                bar.visible = False
            if successful: snack('All files converted successfully', self.page)
            self.page.update()
            
            
class AudioConverter(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page 
        self.create_elements()
        self.setup_layout()
    
    def create_elements(self):
        self.convert_label = ft.Text('Convert to: ', style=ft.TextStyle(size=22))
        self.format_dd = self.create_format_dropdown()
        self.codec_dd = self.create_codec_dropdown()
        self.progress_bar_overall_label = ft.Text(value="Overall Progress", visible=False)
        self.progress_bar_overall = self.create_progress_bar(label="Overall Progress")
        self.progress_bar_file_label = ft.Text(value="", visible=False)
        self.progress_bar_file = self.create_progress_bar(label="File Progress")
        self.file_picker = FilePicker(self.page, ft.FilePickerFileType.AUDIO)
        self.convert_button = ft.ElevatedButton('Convert', icon=ft.icons.TASK_ALT, on_click=self.convert, disabled=True)

    def setup_layout(self):
        format_row = ft.Row([
            self.convert_label,
            self.format_dd,
            self.codec_dd
        ])
        
        convert_row = ft.Row([
            self.convert_button
        ])

        title_label = LabelTitle('Audio files converter')

        self.controls = [title_label, self.file_picker, format_row, convert_row, self.progress_bar_overall_label, self.progress_bar_overall, self.progress_bar_file_label, self.progress_bar_file]

    def create_format_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            width=150,
            label='Format',
            border_radius=10,
            options=[ft.dropdown.Option(fmt) for fmt in ['wav', 'mp3', 'aac', 'm4a', 'ogg', 'flac', 'opus']],
            padding=15,
            on_change=self.dd_codec
        )


    def create_codec_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            width=250,
            label='Codec',
            border_radius=10,
            options=[ft.dropdown.Option('-')],
            padding=15
        )

    def create_progress_bar(self, label: str) -> ft.ProgressBar:
        return ft.ProgressBar(width=500, height=8, visible=False, tooltip=label)

    def dd_codec(self, event):
        format_codecs = {
            # Audio
            'wav': ['pcm_s16le'],
            'mp3': ['libmp3lame'],
            'aac': ['aac', 'libfdk_aac'],
            'm4a': ['aac', 'alac'],
            'ogg': ['libvorbis'],
            'flac': ['flac'],
            'opus': ['opus']
        }
        self.format_selected = self.format_dd.value
        codecs = format_codecs.get(self.format_selected, ['-'])
        self.codec_dd.options = [ft.dropdown.Option(codec) for codec in codecs]
        self.codec_dd.value = codecs[0]
        if self.format_selected:
            self.convert_button.disabled = False
        self.page.update()

    def convert(self, event):
        files = self.file_picker.selected_files
        if files:
            successful = True
            total_files = len(files)
            codec_selected = self.codec_dd.value

            self.progress_bar_overall_label.visible = True
            self.progress_bar_overall.visible = True
            self.progress_bar_file_label.visible = True
            self.progress_bar_file.visible = True
            self.progress_bar_overall.value = 0
            self.page.update()

            for index, file in enumerate(files):
                try:
                    clip = moviepy.AudioFileClip(file.path)
                    base_path = '.'.join(file.path.split('.')[:-1])
                    output_path = generate_unique_filename(base_path, self.format_selected)
                    self.filename = output_path.split('\\')[-1]+' '

                    self.progress_bar_file_label.value = f"Converting {self.filename}"
                    self.page.update()

                    logger = CustomBarLogger(self.page, self.progress_bar_file, self.progress_bar_file_label, self.filename)
                    clip.write_audiofile(output_path, codec=codec_selected, logger=logger, fps=48000 if codec_selected == 'opus' else None)
                except Exception as e:
                    print(f"Error converting file {file.path}: {e}")
                    snack(f"Error converting file {file.path}: {e}", self.page)
                    successful = False
                finally:
                    self.progress_bar_overall_label.value = f'Overall Progress {index + 1}/{total_files}'
                    self.progress_bar_overall.value = (index + 1) / total_files
                    self.page.update()

            
            self.progress_bar_overall_label.value = 'Overall Progress'
            for bar in [self.progress_bar_overall_label,  self.progress_bar_overall,  
                        self.progress_bar_file_label, self.progress_bar_file]:
                bar.visible = False
            if successful: snack('All files converted successfully', self.page)
            self.page.update()
        

class ImageConverter(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.create_elements()
        self.setup_layout()
        
    def create_elements(self):
        self.convert_label = ft.Text('Convert to: ', style=ft.TextStyle(size=22))
        self.format_dd = self.create_format_dropdown()
        self.quality_dd = self.create_quality_dropdown()
        self.file_picker = FilePicker(self.page, ft.FilePickerFileType.IMAGE)
        self.progress_bar_overall_label = ft.Text(value="Overall Progress", visible=False)
        self.progress_bar_overall = self.create_progress_bar(label="Overall Progress")
        self.convert_button = ft.ElevatedButton('Convert', icon=ft.icons.TASK_ALT, on_click=self.convert, disabled=True)
        
    def setup_layout(self):
        format_row = ft.Row([
            self.convert_label,
            self.format_dd,
            self.quality_dd
        ])
        
        convert_row = ft.Row([
            self.convert_button
        ])
        
        title_label = LabelTitle('Image files converter')
        self.controls = [title_label, self.file_picker, format_row, convert_row, self.progress_bar_overall_label, self.progress_bar_overall]
    
    def create_format_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            width=150,
            label='Format',
            border_radius=10,
            options=[ft.dropdown.Option(fmt) for fmt in ["JPEG", "PNG", "GIF", "BMP", "TIFF", "WebP"]],
            padding=15,
            on_change=self.convert_enable
        )
    
    def create_quality_dropdown(self) -> ft.Dropdown:
        return ft.Dropdown(
            width=150,
            label='Quality',
            border_radius=10,
            options=[ft.dropdown.Option(fmt) for fmt in ['High', 'Medium', 'Low']],
            padding=15,
            value='High'
        )
    
    def create_progress_bar(self, label: str) -> ft.ProgressBar:
        return ft.ProgressBar(width=500, height=8, visible=False, tooltip=label)

    def convert_enable(self, event):
        quality_dict = {
            'High': 90,
            'Medium': 55,
            'Low': 25
        }
        
        self.format_selected = self.format_dd.value
        self.quality_selected = quality_dict[str(self.quality_dd.value)]
        if self.format_selected:
            self.convert_button.disabled = False
        self.page.update()
    
    def convert(self, event):
        files = self.file_picker.selected_files
        if files:
            successful = True
            total_files = len(files)
            for index, file in enumerate(files):
                base_path = '.'.join(file.path.split('.')[:-1])
                output_path = generate_unique_filename(base_path, self.format_selected)
                self.filename = output_path.split('\\')[-1]
                try:
                    image = Image.open(file.path)
                    image.save(output_path, format=self.format_selected, quality=self.quality_selected)
                except Exception as e:
                    print(f"Error converting file {file.path}: {e}")
                    snack(f"Error converting file {file.path}: {e}", self.page)
                    successful = False
                finally:
                    self.progress_bar_overall_label.value = f'Overall Progress {index + 1}/{total_files}'
                    self.progress_bar_overall.value = (index + 1) / total_files
                    self.page.update()

            
            self.progress_bar_overall_label.value = 'Overall Progress'
            self.progress_bar_overall_label.visible = False
            self.progress_bar_overall.visible = False

            if successful: snack('All files converted successfully', self.page)
            self.page.update()
        

class Settings(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.create_elements()
        self.setup_layout()
    
    def create_elements(self):
        self.dd_check_theme = ft.Dropdown(label='Theme mode', width=150, options=[ft.dropdown.Option('System'), ft.dropdown.Option('Dark'), ft.dropdown.Option('Light')], on_change=self.change_theme)
        self.btn_dev = ft.IconButton(icon=ft.icons.DEVELOPER_MODE, tooltip='Contact with developer', url='https://t.me/dexering')
        
    def setup_layout(self):
        theme_row = ft.Row([
            ft.Icon(ft.icons.LIGHT_MODE),
            self.dd_check_theme,
            ft.Container(content=self.btn_dev, margin=ft.Margin(400, 0, 0, 0)),
        ])
        
        self.controls = [theme_row]
        
    def change_theme(self, event):
        self.page.theme_mode = self.dd_check_theme.value.lower()
        self.page.update()
        
        
def main(page: ft.Page):
    page.clean()
    page.title = 'Converter'
    page.theme_mode = 'system'
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.width = 800
    page.window.height = 600
    page.window.resizable = False
    page.window.maximizable = False
    page.padding = 10

    
    video_panel = VideoConverter(page)
    
    audio_panel = AudioConverter(page)
    
    image_panel = ImageConverter(page)
    
    settings_panel = Settings(page)
    
    def navigate(event):
        page.clean()
        index = navigation_bar.selected_index
        if index == 0:
            selected_panel = video_panel
        elif index == 1:
            selected_panel = audio_panel
        elif index == 2:
            selected_panel = image_panel
        elif index == 3:
            selected_panel = settings_panel
        page.add(ft.Row([navigation_bar, divider, selected_panel], expand=True))
        page.update()
        
    navigation_bar = ft.NavigationRail(
        label_type=ft.NavigationRailLabelType.ALL,
        height=page.window.height,
        on_change=navigate,
        selected_index=0,
        min_width=100,
        destinations=[
            ft.NavigationRailDestination(icon=ft.icons.VIDEO_FILE, label='Video'),
            ft.NavigationRailDestination(icon=ft.icons.AUDIO_FILE, label='Audio'),
            ft.NavigationRailDestination(icon=ft.icons.IMAGE, label='Image'),
            ft.NavigationRailDestination(icon=ft.icons.SETTINGS, label='Settings')
        ]     
    )
    
    divider = ft.VerticalDivider(width=1)

    page.add(ft.Row(
        [  
            navigation_bar,
            divider,
            video_panel
        ],
        expand=True
    ))

ft.app(target=main)
