
from typing import Optional, Sequence, List

from pymap.interfaces.message import AppendMessage
from pymap.mime import MessageContent
from sievelib.commands import Command  # type: ignore

from .tests import SieveTest

__all__ = ['SieveRunner']


class StopRunning(Exception):
    pass


class SieveRunner:

    def __init__(self, commands: Sequence[Command]) -> None:
        super().__init__()
        self._commands = commands

    def get_actions(self, sender: str, recipient: str,
                    append_msg: AppendMessage) -> Sequence[Command]:
        actions: List[Command] = []
        try:
            content = MessageContent.parse(append_msg.message)
            self._get_actions(actions, sender, recipient, append_msg, content)
        except StopRunning:
            pass
        return actions

    def _get_actions(self, actions: List[Command], sender: str, recipient: str,
                     append_msg: AppendMessage, content: MessageContent) \
            -> None:
        running_if: Optional[Command] = None
        for cmd in self._commands:
            cmd_type = cmd.get_type()
            if cmd_type == 'action':
                actions.append(cmd)
            elif cmd_type == 'control':
                if cmd.name == 'if':
                    running_if = cmd
                elif cmd.name in ('elsif', 'else'):
                    pass
                elif cmd.name == 'stop':
                    raise StopRunning()
                elif cmd.name == 'require':
                    pass
                else:
                    raise NotImplementedError(cmd.name)
            else:
                raise NotImplementedError(cmd_type)
            if running_if:
                if cmd.name in ('if', 'elsif'):
                    test = SieveTest.of(cmd.arguments['test'])
                    test_result = test.run(sender, recipient, append_msg,
                                           content)
                    if not test_result:
                        continue
                elif cmd.name == 'else':
                    pass
                else:
                    running_if = None
                    continue
                running_if = None
                runner = SieveRunner(cmd.children)
                runner._get_actions(actions, sender, recipient, append_msg,
                                    content)
