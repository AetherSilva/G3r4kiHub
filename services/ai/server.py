from concurrent import futures
import grpc
import time
import uuid
import os

import services_pb2
import services_pb2_grpc


class AIServiceServicer(services_pb2_grpc.AIServiceServicer):
    def GenerateText(self, request, context):
        content = f"[deterministic] {request.prompt[::-1]}"
        reply = services_pb2.TextReply(id=str(uuid.uuid4()), content=content, tokens_used=len(request.prompt.split()))
        return reply

    def GenerateImage(self, request, context):
        img_id = str(uuid.uuid4())
        path = f"/srv/images/{img_id}.png"
        return services_pb2.ImageReply(id=img_id, url=path)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    services_pb2_grpc.add_AIServiceServicer_to_server(AIServiceServicer(), server)
    port = os.getenv("AI_SERVICE_PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
