# GrapheryExecutor

Graphery Executor Module is a python script execution sever and part of Graphery V2. It's inspired
by [PySnooper](https://github.com/cool-RR/PySnooper) and [PyTutor](https://github.com/okpy/pytutor) and uses a wrapped
version of [NetworkX](https://github.com/Reed-CompBio/networkx) for graph support.

This set of scripts works with Graphery, and unlike the remote version provided by Graphery, this one can be used
without restrictions.

## Get Started

There are two ways to start the executor server, one through scripts and one through docker. The python minimal version
is `3.10`.

First, to install the executor,

1. To run through shell commands, `executor` has to be installed first through the following commands:

   ```shell
   # in the directory where you want to install graphery executor
   python --version
   # make sure the python version is above or equal to 3.10
   python -m venv ./venv
   # switch into virtual environment to install
   source ./venv/bin/activate
   pip install .
   deactivate
   ```

   To run the executor, use the following command
   ```shell
   source ./venv/bin/activate
   graphery_executor server
   # press ctrl + c to exit 
   deactivate
   ```
## Get Started with Docker
To run through docker,
   ```shell
   docker compose up --build 
   ```

## Usage

For the following python code:

```python
# `tracer`, `peek`, and `networkx` are injected 
# so no importing is needed 

# Wanna to access the tutorial graph? 
# It's injected, too! just use `graph` in the code!
from networkx import Graph


@peek
def test_peek(a, b):
    return a * b


@tracer('a', 'b')
def test_tracer(a, b, c):
    a = test_peek(a, c)
    b = test_peek(b, c)
    c = test_peek(c, c)
    graph.add_nodes_from(
        [a, b, c]
    )
    graph.add_edges_from([(a, b), (b, c)])
    return graph


test_tracer(7, 9, 11)
```

, the request with some graph to the executor can be

```json
{
  "code": "@tracer('a', 'b')\ndef test(a, b, c):\n    a = a * c\n    b = b * c\n    c = c * c\n    return a + b * c\n\ntest(7, 9, 11)",
  "graph": "{\"data\":[],\"directed\":false,\"multigraph\":false,\"elements\":{\"nodes\":[{\"data\":{\"id\":\"1\",\"value\":1,\"name\":\"1\"}},{\"data\":{\"id\":\"2\",\"value\":2,\"name\":\"2\"}},{\"data\":{\"id\":\"3\",\"value\":3,\"name\":\"3\"}},{\"data\":{\"id\":\"4\",\"value\":4,\"name\":\"4\"}},{\"data\":{\"id\":\"7\",\"value\":7,\"name\":\"7\"}},{\"data\":{\"id\":\"5\",\"value\":5,\"name\":\"5\"}},{\"data\":{\"id\":\"6\",\"value\":6,\"name\":\"6\"}}],\"edges\":[{\"data\":{\"source\":1,\"target\":2}},{\"data\":{\"source\":1,\"target\":3}},{\"data\":{\"source\":3,\"target\":4}},{\"data\":{\"source\":4,\"target\":5}},{\"data\":{\"source\":7,\"target\":5}},{\"data\":{\"source\":5,\"target\":5}}]}}",
  "version": "3.1.0",
  "options": {
    "rand_seed": 0,
    "float_precision": 5
  }
}
```

in which the `version` field has to match the executor version to make the request acceptable. The option is detailed here (link coming soon). 

Once the request is executed, the server will return a response like the following whose structure is detailed here (link coming soon). 

```json
{
  "errors": null,
  "info": {
    "result": [
      {
        "line": 0,
        "variables": {
          "test_tracer\u200b@a": {
            "type": "init",
            "color": "#A6CEE3",
            "repr": null
          },
          "test_tracer\u200b@b": {
            "type": "init",
            "color": "#1F78B4",
            "repr": null
          }
        },
        "accesses": null,
        "stdout": null
      },
      {
        "line": 15,
        "variables": {
          "test_tracer\u200b@a": {
            "type": "Number",
            "python_id": 140284831269296,
            "color": "#A6CEE3",
            "repr": "7"
          },
          "test_tracer\u200b@b": {
            "type": "Number",
            "python_id": 140284831269360,
            "color": "#1F78B4",
            "repr": "9"
          }
        },
        "accesses": null,
        "stdout": null
      },
      {
        "line": 16,
        "variables": {
          "test_tracer\u200b@a": {
            "type": "Number",
            "python_id": 140284831271536,
            "color": "#A6CEE3",
            "repr": "77"
          },
          "test_tracer\u200b@b": {
            "type": "Number",
            "python_id": 140284831269360,
            "color": "#1F78B4",
            "repr": "9"
          }
        },
        "accesses": [
          {
            "type": "Number",
            "python_id": 140284831271536,
            "color": "#B15928",
            "repr": "77"
          }
        ],
        "stdout": null
      },
      {
        "line": 17,
        "variables": {
          "test_tracer\u200b@a": {
            "type": "Number",
            "python_id": 140284831271536,
            "color": "#A6CEE3",
            "repr": "77"
          },
          "test_tracer\u200b@b": {
            "type": "Number",
            "python_id": 140284831272240,
            "color": "#1F78B4",
            "repr": "99"
          }
        },
        "accesses": [
          {
            "type": "Number",
            "python_id": 140284831272240,
            "color": "#B15928",
            "repr": "99"
          }
        ],
        "stdout": null
      },
      {
        "line": 18,
        "variables": null,
        "accesses": [
          {
            "type": "Number",
            "python_id": 140284831272944,
            "color": "#B15928",
            "repr": "121"
          }
        ],
        "stdout": null
      },
      {
        "line": 19,
        "variables": null,
        "accesses": null,
        "stdout": null
      },
      {
        "line": 20,
        "variables": null,
        "accesses": null,
        "stdout": null
      },
      {
        "line": 19,
        "variables": null,
        "accesses": null,
        "stdout": null
      },
      {
        "line": 22,
        "variables": null,
        "accesses": null,
        "stdout": null
      },
      {
        "line": 23,
        "variables": null,
        "accesses": null,
        "stdout": null
      }
    ]
  }
}
```

There is also a local executor that only receives a request from stdin and output the execution result to stdin and errors to stderr. Detail is listed here (link coming soon). 
