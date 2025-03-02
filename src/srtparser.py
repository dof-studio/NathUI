# srt_parser.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################


from bs4 import BeautifulSoup 
import re

class SRTParser:
    def __init__(self):
        self.entries = []

    @staticmethod
    def parse_time(time_str):
        hours, mins, secs_millis = time_str.split(':')
        secs, millis = secs_millis.split(',')
        return int(hours) * 3600000 + int(mins) * 60000 + int(secs) * 1000 + int(millis)

    @staticmethod
    def format_time(total_ms):
        hours = total_ms // 3600000
        remaining = total_ms % 3600000
        mins = remaining // 60000
        remaining %= 60000
        secs = remaining // 1000
        millis = remaining % 1000
        return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def build_opening_tag(tag_dict):
        tag = tag_dict['name']
        attrs = tag_dict['attrs']
        attr_str = ' '.join([f'{key}="{value}"' for key, value in attrs.items()])
        return f"<{tag} {attr_str}>" if attr_str else f"<{tag}>"

    @staticmethod
    def build_closing_tag(tag_dict):
        return f"</{tag_dict['name']}>"

    def parse(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        current_entry = None
        for line in lines:
            if re.match(r'^\d+$', line):
                if current_entry is not None:
                    self.entries.append(current_entry)
                current_entry = {
                    'number': int(line),
                    'start': None,
                    'end': None,
                    'text_lines': []  # Each line includes its text and formatting tags (with attributes)
                }
            elif '-->' in line:
                start_str, end_str = line.split(' --> ')
                current_entry['start'] = self.parse_time(start_str.strip())
                current_entry['end'] = self.parse_time(end_str.strip())
            else:
                if current_entry is not None:
                    soup = BeautifulSoup(line, 'html.parser')
                    text = soup.get_text()
                    formatting_tags = [{'name': tag.name, 'attrs': tag.attrs} for tag in soup.find_all()]
                    current_entry['text_lines'].append({
                        'text': text,
                        'formatting': formatting_tags
                    })
        if current_entry is not None:
            self.entries.append(current_entry)

    def modify_timestamps(self, entry_index, new_start, new_end):
        if 0 <= entry_index < len(self.entries):
            self.entries[entry_index]['start'] = new_start
            self.entries[entry_index]['end'] = new_end

    def modify_text_line(self, entry_index, line_index, new_text, new_formatting=None):
        if 0 <= entry_index < len(self.entries) and 0 <= line_index < len(self.entries[entry_index]['text_lines']):
            self.entries[entry_index]['text_lines'][line_index]['text'] = new_text
            if new_formatting is not None:
                self.entries[entry_index]['text_lines'][line_index]['formatting'] = new_formatting

    def modify_formatting(self, entry_index, line_index, new_formatting):
        if 0 <= entry_index < len(self.entries) and 0 <= line_index < len(self.entries[entry_index]['text_lines']):
            self.entries[entry_index]['text_lines'][line_index]['formatting'] = new_formatting

    def get_timestamps(self, entry_index):
        if 0 <= entry_index < len(self.entries):
            return self.entries[entry_index]['start'], self.entries[entry_index]['end']
        return None

    def get_text(self, entry_index, line_index):
        if (0 <= entry_index < len(self.entries) and 
            0 <= line_index < len(self.entries[entry_index]['text_lines'])):
            return self.entries[entry_index]['text_lines'][line_index]['text']
        return None

    def get_formatting(self, entry_index, line_index):
        if (0 <= entry_index < len(self.entries) and 
            0 <= line_index < len(self.entries[entry_index]['text_lines'])):
            return self.entries[entry_index]['text_lines'][line_index]['formatting']
        return None

    def save(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                f.write(f"{entry['number']}\n")
                start_time = self.format_time(entry['start'])
                end_time = self.format_time(entry['end'])
                f.write(f"{start_time} --> {end_time}\n")
                for line in entry['text_lines']:
                    if line['formatting']:
                        opening_tags = ''.join([self.build_opening_tag(tag) for tag in line['formatting']])
                        closing_tags = ''.join([self.build_closing_tag(tag) for tag in reversed(line['formatting'])])
                        formatted_text = opening_tags + line['text'] + closing_tags
                    else:
                        formatted_text = line['text']
                    f.write(formatted_text + '\n')
                f.write('\n')

def test_parser_methods():
    parser = SRTParser()
    filename = r'C:\Users\T15P\Downloads\42.srt'
    parser.parse(filename)  # sample.srt should contain your SRT file content
    
    # Testing get_timestamps for the first entry
    timestamps = parser.get_timestamps(0)
    if timestamps:
        start, end = timestamps
        print("Entry 0 Timestamps:", SRTParser.format_time(start), "-->", SRTParser.format_time(end))
    
    # Testing get_text for the first text line of the first entry
    text = parser.get_text(0, 0)
    if text is not None:
        print("Entry 0, Line 0 Text:", text)
    
    # Testing get_formatting for the first text line of the first entry
    formatting = parser.get_formatting(0, 0)
    if formatting is not None:
        print("Entry 0, Line 0 Formatting:", formatting)

if __name__ == '__main__':
    test_parser_methods()

