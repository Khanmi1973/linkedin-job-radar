"""LinkedIn Job Post Finder — run with python app.py."""
import json
import os
import queue
import tkinter as tk
import webbrowser
from dataclasses import asdict
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from core import Filters, SECTORS, AGES, export_csv, safe_url
from scraper import BrowserWorker

DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local' / 'share'))) / 'LinkedInJobFinder'

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('LinkedIn Job Post Finder')
        self.geometry('1180x800')
        self.minsize(960, 680)
        self.configure(bg='#edf2f7')
        DATA.mkdir(parents=True, exist_ok=True)
        self.posts, self.visible, self.busy = {}, [], False
        self.events = queue.Queue()
        self.worker = BrowserWorker(self.events, DATA)
        self.vars = {}
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('TFrame', background='#edf2f7')
        style.configure('TLabel', background='#edf2f7', foreground='#18334b')
        style.configure('TCheckbutton', background='#edf2f7')
        style.configure('TButton', padding=(12, 8))
        style.configure('Primary.TButton', background='#116b65', foreground='white')
        style.configure('Treeview', rowheight=32, background='white', fieldbackground='white')
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), padding=8)
        header = tk.Frame(self, bg='#12334b', padx=24, pady=18)
        header.pack(fill='x')
        tk.Label(header, text='JOB POST FINDER', bg='#12334b', fg='#7dd9c3', font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        tk.Label(header, text='Find your next opportunity in the feed.', bg='#12334b', fg='white', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        tk.Label(header, text='LinkedIn member posts · keyword and sector filters · local results', bg='#12334b', fg='#c3d4df', font=('Segoe UI', 10)).pack(anchor='w', pady=(5, 0))
        body = ttk.Frame(self, padding=18)
        body.pack(fill='both', expand=True)
        side = ttk.Frame(body, width=285)
        side.pack(side='left', fill='y', padx=(0, 20))
        side.pack_propagate(False)
        self.field(side, 'Keywords (comma-separated)', 'keywords')
        self.field(side, 'Match keywords', 'keyword_mode', ['Any keyword', 'All keywords'])
        self.field(side, 'Sector (matched against post text)', 'sector', list(SECTORS))
        self.field(side, 'Custom sector terms (comma-separated)', 'custom_sector')
        self.field(side, 'Post age', 'age', list(AGES))
        self.field(side, 'Location / remote words (optional)', 'location')
        self.field(side, 'Exclude words (comma-separated)', 'exclude')
        for key, label, default in [('people_only', 'People only (verified profile link)', True),
                                    ('hiring_only', 'Require hiring language', True),
                                    ('include_unknown_age', 'Include posts with unknown age', False)]:
            self.vars[key] = tk.BooleanVar(value=default)
            ttk.Checkbutton(side, text=label, variable=self.vars[key]).pack(anchor='w', pady=3)
        ttk.Label(side, text='Maximum scrolls (0–50)').pack(anchor='w', pady=(12, 3))
        self.scrolls = tk.StringVar(value='10')
        ttk.Spinbox(side, from_=0, to=50, textvariable=self.scrolls, width=8).pack(anchor='w')
        ttk.Button(side, text='Apply filters to saved results', command=self.apply).pack(fill='x', pady=(12, 0))
        right = ttk.Frame(body)
        right.pack(side='left', fill='both', expand=True)
        actions = ttk.Frame(right)
        actions.pack(fill='x')
        self.login = ttk.Button(actions, text='1. Open browser / Sign in', command=lambda: self.command('login'))
        self.login.pack(side='left')
        self.find = ttk.Button(actions, text='2. Find posts', style='Primary.TButton', command=self.search)
        self.find.pack(side='left', padx=8)
        self.stop = ttk.Button(actions, text='Stop', command=self.stop_search, state='disabled')
        self.stop.pack(side='left')
        self.count = tk.StringVar(value='0 matching posts')
        ttk.Label(right, textvariable=self.count, font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(20, 8))
        pane = ttk.Panedwindow(right, orient='vertical')
        pane.pack(fill='both', expand=True)
        listing = ttk.Frame(pane)
        self.table = ttk.Treeview(listing, columns=('author', 'age', 'post'), show='headings', selectmode='browse')
        for name, title, width in [('author', 'Posted by', 150), ('age', 'Age', 75), ('post', 'Hiring post', 400)]:
            self.table.heading(name, text=title)
            self.table.column(name, width=width, minwidth=60, stretch=name == 'post')
        bar = ttk.Scrollbar(listing, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y')
        self.table.pack(fill='both', expand=True)
        self.table.bind('<<TreeviewSelect>>', self.select)
        self.table.bind('<Double-1>', lambda event: self.open_post())
        pane.add(listing, weight=3)
        detail = ttk.Frame(pane, padding=(0, 10, 0, 0))
        ttk.Label(detail, text='POST DETAILS', font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.detail = tk.Text(detail, wrap='word', height=9, relief='flat', padx=12, pady=12, font=('Segoe UI', 10), bg='white', state='disabled')
        self.detail.pack(fill='both', expand=True, pady=5)
        pane.add(detail, weight=2)
        self.set_detail('Start with Open browser / Sign in. Log in yourself, then click Find posts.\n\nResults are kept on this computer. Sector, location, and hiring detection are keyword heuristics. No paid API key is needed.')
        footer = ttk.Frame(right)
        footer.pack(fill='x', pady=(10, 0))
        ttk.Button(footer, text='Open selected post', command=self.open_post).pack(side='left')
        ttk.Button(footer, text='Export CSV', command=self.export).pack(side='left', padx=8)
        ttk.Button(footer, text='Clear saved results', command=self.clear).pack(side='right')
        self.status = tk.StringVar(value='Ready. Sign in to LinkedIn in the app’s browser to begin.')
        ttk.Label(self, textvariable=self.status, padding=(18, 10), wraplength=1100).pack(fill='x')
        self.load()
        self.worker.start()
        self.after(100, self.poll)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def field(self, parent, label, key, choices=None):
        ttk.Label(parent, text=label).pack(anchor='w', pady=(7, 3))
        self.vars[key] = tk.StringVar(value=getattr(Filters(), key))
        widget = ttk.Combobox(parent, textvariable=self.vars[key], values=choices, state='readonly') if choices else ttk.Entry(parent, textvariable=self.vars[key])
        widget.pack(fill='x')

    def filters(self):
        return Filters(**{key: value.get().strip() if isinstance(value, tk.StringVar) else value.get() for key, value in self.vars.items()})

    def command(self, name, payload=None):
        if self.busy:
            return
        if not self.worker.is_alive():
            messagebox.showerror('Browser unavailable', 'Restart the app. If Playwright is missing, run Setup.cmd first.')
            return
        self.busy = True
        self.worker.cancel.clear()
        self.login.configure(state='disabled')
        self.find.configure(state='disabled')
        self.stop.configure(state='normal')
        self.worker.commands.put((name, payload))

    def search(self):
        try:
            maximum = int(self.scrolls.get())
            if not 0 <= maximum <= 50:
                raise ValueError()
        except ValueError:
            messagebox.showerror('Check scroll limit', 'Enter a whole number from 0 to 50.')
            return
        if self.vars['sector'].get() == 'Custom sector' and not self.vars['custom_sector'].get().strip():
            messagebox.showerror('Custom sector', 'Enter at least one custom sector term.')
            return
        self.apply()
        self.command('search', (self.filters(), maximum))

    def stop_search(self):
        self.worker.cancel.set()
        self.status.set('Stopping after the current browser operation…')

    def apply(self):
        filters = self.filters()
        self.visible = [post for post in self.posts.values() if filters.matches(post)]
        self.table.delete(*self.table.get_children())
        for index, post in enumerate(self.visible):
            self.table.insert('', 'end', iid=str(index), values=(post['author'], post['age'] or 'Unknown', ' '.join(post['text'].split())[:180]))
        self.count.set(f'{len(self.visible)} matching posts  /  {len(self.posts)} collected')
        self.set_detail('Select a result to read its post text. If no posts match, broaden your filters or allow unknown post ages.')
        self.save()

    def set_detail(self, text):
        self.detail.configure(state='normal')
        self.detail.delete('1.0', 'end')
        self.detail.insert('1.0', text)
        self.detail.configure(state='disabled')

    def selected(self):
        selection = self.table.selection()
        return self.visible[int(selection[0])] if selection else None

    def select(self, event=None):
        post = self.selected()
        if post:
            self.set_detail(f"{post['author']} · {post['age'] or 'Unknown age'} at collection\n{post['url'] or 'No direct post link available'}\n\n{post['text']}\n\nCollected: {post['collected_at']}")

    def open_post(self):
        post = self.selected()
        if not post:
            messagebox.showinfo('Choose a post', 'Select a result first.')
        elif safe_url(post.get('url', '')):
            webbrowser.open(post['url'])
        else:
            messagebox.showinfo('No link available', 'LinkedIn did not expose a direct link for this post.')

    def export(self):
        if not self.visible:
            messagebox.showinfo('No results', 'There are no matching posts to export.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='linkedin-hiring-posts.csv', filetypes=[('CSV spreadsheet', '*.csv')])
        if path:
            try:
                export_csv(path, self.visible)
                self.status.set(f'Exported {len(self.visible)} matching posts to {path}')
            except OSError as error:
                messagebox.showerror('Export failed', str(error))

    def clear(self):
        if self.busy:
            messagebox.showinfo('Collection running', 'Stop collection before clearing saved results.')
        elif messagebox.askyesno('Clear results', 'Delete all locally saved posts? Your LinkedIn sign-in will be kept.'):
            self.posts.clear()
            self.apply()

    def save(self):
        try:
            target = DATA / 'results.json'
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps({'filters': asdict(self.filters()), 'posts': list(self.posts.values())}, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(target)
        except OSError as error:
            self.status.set(f'Could not save results: {error}')

    def load(self):
        path = DATA / 'results.json'
        if not path.exists():
            return
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
            for key, value in saved.get('filters', {}).items():
                if key in self.vars:
                    if key == 'age' and value not in AGES or key == 'sector' and value not in SECTORS:
                        continue
                    self.vars[key].set(value)
            self.posts = {post['id']: post for post in saved.get('posts', [])}
            self.apply()
        except (ValueError, KeyError, TypeError, OSError) as error:
            self.status.set(f'Saved results could not be loaded: {error}')

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == 'status':
                    self.status.set(payload)
                elif kind == 'posts':
                    self.posts.update({post['id']: post for post in payload})
                    self.apply()
                elif kind == 'error':
                    self.status.set('Collection could not finish. See the error message.')
                    messagebox.showerror('Browser message', payload)
                elif kind == 'done':
                    self.busy = False
                    self.login.configure(state='normal')
                    self.find.configure(state='normal')
                    self.stop.configure(state='disabled')
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def close(self):
        self.save()
        self.worker.cancel.set()
        self.worker.closing.set()
        self.withdraw()
        self.await_shutdown()

    def await_shutdown(self):
        if self.worker.is_alive():
            self.after(100, self.await_shutdown)
        else:
            self.destroy()

if __name__ == '__main__':
    App().mainloop()
