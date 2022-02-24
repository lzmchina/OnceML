from .TorchServingUtils import outputMar,run_ts_serving
from .config import inference_port as TS_INFERENCE_PORT
from .config import management_port as TS_MANAGEMENT_PORT
import os
import string
TS_PROPERTIES_FILE = "ts.properties"
TS_PROPERTIES_PATH=os.path.join(__path__[0], TS_PROPERTIES_FILE)
string.Template("""
    # cors_allowed_origin is required to enable CORS, use '*' or your domain name
    cors_allowed_origin=*
    # required if you want to use preflight request
    cors_allowed_methods=GET, POST, PUT, OPTIONS
    # required if the request has an Access-Control-Request-Headers header
    #cors_allowed_headers=X-Custom-Header
    inference_address=http://0.0.0.0:${inference_port}
"""
)
