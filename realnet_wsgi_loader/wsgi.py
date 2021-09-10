import logging
logging.basicConfig(level=logging.DEBUG)

import realnet_server
print(dir(realnet_server))
app = realnet_server.app