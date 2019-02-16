
import ipaddress
import socket as _socket
from abc import abstractmethod, ABCMeta
from asyncio import BaseTransport, StreamWriter
from typing import Any, Union, Optional, Tuple, Sequence, Mapping, List

try:
    import systemd.daemon  # type: ignore
except ImportError as exc:
    systemd_import_exc: Optional[ImportError] = exc
else:
    systemd_import_exc = None

__all__ = ['InheritedSockets', 'SocketInfo']

_Transport = Union[BaseTransport, StreamWriter]
_PeerName = Union[Tuple[str, int], Tuple[str, int, int, int], str]
_PeerCert = Mapping[str, Any]  # {'issuer': ..., ...}


class InheritedSockets(metaclass=ABCMeta):
    """Abstracts the ability to retrieve inherited sockets from the calling
    process, usually a service management framework.

    """

    @abstractmethod
    def get(self) -> Sequence[_socket.socket]:
        """Return the sockets inherited by the process."""
        ...

    @classmethod
    def of(cls, service_manager: str) -> 'InheritedSockets':
        """Return the inherited sockets for the given service manager.

        Note:
            Only ``'systemd'`` is implemented at this time.

        Args:
            service_manager: The service manager name.

        """
        if service_manager == 'systemd':
            return cls.for_systemd()
        else:
            raise KeyError(service_manager)

    @classmethod
    def for_systemd(cls) -> 'InheritedSockets':
        """Return the inherited sockets for `systemd`_. The `python-systemd`_
        library must be installed.

        See Also:
            `systemd.socket`_, `sd_listen_fds`_

        .. _systemd: https://freedesktop.org/wiki/Software/systemd/
        .. _systemd.socket: https://www.freedesktop.org/software/systemd/man/systemd.socket.html
        .. _sd_listen_fds: https://www.freedesktop.org/software/systemd/man/sd_listen_fds.html
        .. _python-systemd: https://github.com/systemd/python-systemd

        Raises:
            :exc:`NotImplementedError`

        """  # noqa: E501
        if systemd_import_exc:
            raise systemd_import_exc
        return _SystemdSockets()


class _SystemdSockets(InheritedSockets):

    def __init__(self) -> None:
        super().__init__()
        fds: Sequence[int] = systemd.daemon.listen_fds()
        sockets: List[_socket.socket] = []
        for fd in fds:
            family = self._get_family(fd)
            sock = _socket.fromfd(fd, family, _socket.SOCK_STREAM)
            sockets.append(sock)
        self._sockets = sockets

    def get(self) -> Sequence[_socket.socket]:
        return self._sockets

    @classmethod
    def _get_family(cls, fd: int) -> int:
        if systemd.daemon.is_socket(fd, _socket.AF_UNIX):
            return _socket.AF_UNIX
        elif systemd.daemon.is_socket(fd, _socket.AF_INET6):
            return _socket.AF_INET6
        else:
            return _socket.AF_INET


class SocketInfo:
    """Information about a connected socket, which may be useful for
    server-side logic such as authentication and authorization.

    Attribute access is passed directly into
    :meth:`~asyncio.BaseTransport.get_extra_info`, decorated in some cases with
    type hints and checks.

    See Also:
        :meth:`~asyncio.BaseTransport.get_extra_info`

    """

    __slots__ = ['_transport']

    def __init__(self, transport: _Transport) -> None:
        super().__init__()
        self._transport = transport

    @property
    def socket(self) -> _socket.socket:
        sock = self._transport.get_extra_info('socket')
        if sock is None:
            raise ValueError('socket')
        return sock

    @property
    def peername(self) -> _PeerName:
        peername = self._transport.get_extra_info('peername')
        if peername is None:
            raise ValueError('peername')
        return peername

    @property
    def peercert(self) -> Optional[_PeerCert]:
        return self._transport.get_extra_info('peercert')

    @property
    def from_localhost(self) -> bool:
        """True if :attr:`.peername` is a connection from a ``localhost``
        address.

        """
        sock_family = self.socket.family
        if sock_family == _socket.AF_UNIX:
            return True
        elif sock_family not in (_socket.AF_INET, _socket.AF_INET6):
            return False
        sock_address, *_ = self.peername
        ip = ipaddress.ip_address(sock_address)
        if ip.version == 6 and ip.ipv4_mapped is not None:
            ip = ipaddress.ip_address(ip.ipv4_mapped)
        return ip.is_loopback

    def __getattr__(self, name: str) -> Any:
        return self._transport.get_extra_info(name)

    def __str__(self) -> str:
        return '<SocketInfo peername=%r sockname=%r peercert=%r>' \
            % (self.peername, self.sockname, self.peercert)

    def __bytes__(self) -> bytes:
        return bytes(str(self), 'utf-8', 'replace')