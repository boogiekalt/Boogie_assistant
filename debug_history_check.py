from pathlib import Path
from unittest.mock import patch
from commands import AssistantEngine

path = Path('.')
file = path / 'conversation_history.json'
if file.exists():
    file.unlink()
engine = AssistantEngine(path)
print('initial', list(engine.conversation_history))
with patch.object(engine, '_ask_local_model', side_effect=['Salut !', 'Tu as demandé : comment ça va.']) as local_model:
    first = engine.process('bonjour', mode='conversation')
    print('after first', list(engine.conversation_history), first)
    second = engine.process('qu est ce que je viens de te demander', mode='conversation')
    print('after second', list(engine.conversation_history), second)
    print('call_count', local_model.call_count)
