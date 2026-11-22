"""Disposable loopback-only SMTP capture for browser tests; never deploy as mail infrastructure."""
import argparse
import os
from pathlib import Path
import signal
from threading import Event
from uuid import uuid4
from aiosmtpd.controller import Controller


class Sink:
    def __init__(self,directory): self.directory=directory

    async def handle_DATA(self,server,session,envelope):
        name=uuid4().hex
        temporary=self.directory/(name+'.tmp')
        final=self.directory/(name+'.eml')
        with temporary.open('xb') as out:
            out.write(envelope.original_content)
        os.replace(temporary,final)
        return '250 Message accepted for disposable testing'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',default='/tmp/elvaa-test-mail')
    parser.add_argument('--port',type=int,default=1025)
    args=parser.parse_args()
    os.umask(0o077)
    directory=Path(args.directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    controller=Controller(Sink(directory),hostname='127.0.0.1',port=args.port)
    stop=Event()
    signal.signal(signal.SIGTERM,lambda *_:stop.set())
    signal.signal(signal.SIGINT,lambda *_:stop.set())
    controller.start()
    print(f'Test SMTP sink listening on 127.0.0.1:{args.port}; messages in {directory}',flush=True)
    try: stop.wait()
    finally: controller.stop()


if __name__=='__main__': main()
