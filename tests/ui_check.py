"""UI smoke check with isolated synthetic data, no LinkedIn network access."""
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

with tempfile.TemporaryDirectory() as directory:
    app.DATA = Path(directory)
    window = app.App()
    window.withdraw()
    window.posts = {'fixture': dict(id='fixture', author='Demo Recruiter', author_type='person',
                                  text='We are hiring a Python developer', age='2h', url='',
                                  collected_at=datetime.now(timezone.utc).isoformat())}
    window.apply()
    window.update()
    assert len(window.table.get_children()) == 1
    window.table.selection_set('0')
    window.select()
    assert 'Python developer' in window.detail.get('1.0', 'end')
    window.vars['keywords'].set('nurse')
    window.apply()
    assert not window.table.get_children()
    assert (app.DATA / 'results.json').exists()
    window.close()
    window.mainloop()
print('PASS: Tk desktop initialization, results, selection, filtering, saving and clean shutdown')
