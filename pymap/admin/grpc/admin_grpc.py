# Generated by the Protocol Buffers compiler. DO NOT EDIT!
# source: pymap/admin/grpc/admin.proto
# plugin: grpclib.plugin.main
import abc

import grpclib.const
import grpclib.client

import pymap.admin.grpc.admin_pb2


class AdminBase(abc.ABC):

    @abc.abstractmethod
    async def Append(self, stream):
        pass

    def __mapping__(self):
        return {
            '/admin.Admin/Append': grpclib.const.Handler(
                self.Append,
                grpclib.const.Cardinality.UNARY_UNARY,
                pymap.admin.grpc.admin_pb2.AppendRequest,
                pymap.admin.grpc.admin_pb2.AppendResponse,
            ),
        }


class AdminStub:

    def __init__(self, channel: grpclib.client.Channel) -> None:
        self.Append = grpclib.client.UnaryUnaryMethod(
            channel,
            '/admin.Admin/Append',
            pymap.admin.grpc.admin_pb2.AppendRequest,
            pymap.admin.grpc.admin_pb2.AppendResponse,
        )
