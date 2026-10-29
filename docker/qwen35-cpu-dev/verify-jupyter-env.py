#!/usr/bin/env python3
"""Verify pinned packages, an executing kernel, and both authenticated web UIs."""
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


EXPECTED = {
    "ipython": "8.12.2",
    "notebook": "6.5.2",
    "jupyterlab": "4.5.11",
    "jupyterlab-language-pack-zh-CN": "4.5.post3",
    "traitlets": "5.9.0",
}


def verify_server(module, app, route, root):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    # This token exists only for the isolated, short-lived test server.
    token = "qwen35-build-verification"
    command = [
        sys.executable, "-m", module, "--no-browser", "--allow-root",
        f"--{app}.ip=127.0.0.1", f"--{app}.port={port}",
        f"--{app}.port_retries=0", f"--{app}.token={token}",
    ]
    if app == "ServerApp":
        command.append(f"--ServerApp.root_dir={root}")
        command.append("--LabApp.check_for_updates_class=jupyterlab.NeverCheckForUpdate")
    else:
        command.append(f"--NotebookApp.notebook_dir={root}")
    env = dict(os.environ)
    for key in ("JUPYTER_CONFIG_DIR", "JUPYTER_RUNTIME_DIR", "IPYTHONDIR"):
        env[key] = str(root / f"{module}-{key.lower()}")
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f"{module} exited with {process.returncode}")
                try:
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{port}/api/status",
                        headers={"Authorization": f"token {token}"},
                    )
                    with urllib.request.urlopen(request, timeout=2) as response:
                        status = json.load(response)
                    assert "kernels" in status, status
                    break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError(f"{module} startup timed out")
                    time.sleep(0.2)
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}{route}",
                headers={"Authorization": f"token {token}"},
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                assert response.status == 200
                assert "text/html" in response.headers["Content-Type"]
                assert len(response.read()) > 100
            print(f"PASS: {module} authenticated /api/status and {route}")
        except BaseException:
            log.seek(0)
            print(log.read(), file=sys.stderr)
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main():
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
    for package, expected in EXPECTED.items():
        actual = metadata.version(package)
        assert actual == expected, (package, actual, expected)
        print(f"{package}=={actual}")
    language_pack = metadata.distribution("jupyterlab-language-pack-zh-CN")
    assert any(str(path).endswith(".mo") for path in language_pack.files)
    print("PASS: Chinese language pack translation files installed")

    import nbformat
    from nbclient import NotebookClient

    with tempfile.TemporaryDirectory(prefix="verify-jupyter-") as temporary:
        root = Path(temporary)
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
            "import IPython, sys\n"
            "assert IPython.__version__ == '8.12.2'\n"
            "assert sum(range(64)) == 2016\n"
            "print('kernel-execution-ok')"
        )])
        client = NotebookClient(notebook, timeout=60, kernel_name="python3",
                                resources={"metadata": {"path": temporary}})
        client.execute()
        outputs = notebook.cells[0].outputs
        assert any("kernel-execution-ok" in output.get("text", "") for output in outputs)
        print("PASS: Python kernel executed a notebook cell")
        verify_server("jupyterlab", "ServerApp", "/lab", root)
        verify_server("notebook", "NotebookApp", "/tree", root)
    print("PASS: Jupyter dependencies, kernel execution, JupyterLab and Notebook HTTP checks")


if __name__ == "__main__":
    main()
