import re

with open('src/shortcircuit/app.py', 'r') as f:
    content = f.read()

# Fix login_handler to use the dict signal
old_handler = r'''    @QtCore.Slot\(bool, str, int\)
    def login_handler\(self, is_ok, char_name=None, char_id=0\):
        # Handle cases where PySide might mangle the argument list across threads
        if isinstance\(char_name, int\) and char_id == 0:
            char_id = char_name
            char_name = "Unknown"
            
        self.state_eve_connection\["connected"\] = is_ok
        self.state_eve_connection\["char_name"\] = char_name
        self.state_eve_connection\["char_id"\] = char_id if is_ok else 0
        self.state_eve_connection\["error"\] = "ESI error" if not is_ok else None
        
        Logger.info\(f"Login handler received: ok={is_ok}, name={char_name}, id={char_id}"\)
        self._status_eve_connection_update\(\)'''

new_handler = r'''    @QtCore.Slot(dict)
    def login_handler(self, result):
        is_ok = result.get('is_ok', False)
        char_name = result.get('char_name', 'Unknown')
        char_id = int(result.get('char_id', 0))

        self.state_eve_connection["connected"] = is_ok
        self.state_eve_connection["char_name"] = char_name
        self.state_eve_connection["char_id"] = char_id if is_ok else 0
        self.state_eve_connection["error"] = "ESI error" if not is_ok else None

        Logger.info(f"Login handler received dict: ok={is_ok}, name={char_name}, id={char_id}")
        self._status_eve_connection_update()'''

content = re.sub(old_handler, new_handler, content)

with open('src/shortcircuit/app.py', 'w') as f:
    f.write(content)
