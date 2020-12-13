"""
IPython magic, specifically for Jupyter, allowing memory profiling from inside
a Jupyter notebook.
"""

from pathlib import Path
from textwrap import indent
from contextlib import contextmanager

from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.display import IFrame, display

from ._tracer import start_tracing, stop_tracing, disable_thread_pools


HOPEFULLY_UNIQUE_VAR = "__arghbldsada__"

# We use a variable that is unlikely to conflict with user code.
# We also:
#
# 1. Make sure line numbers line up with original code (first line is a magic,
#    so we can put stuff there!)
# 2. Make sure user code runs in a function, so top-level lines get recorded.
TEMPLATE = """\
def __magic_run_with_fil():
{}
with {}(): __magic_run_with_fil()
"""


@magics_class
class FilMagics(Magics):
    """Magics for memory profiling."""

    @cell_magic
    def filprofile(self, line, cell):
        """Memory profile the code in the cell."""
        # Inject run_with_profile:

        self.shell.push({HOPEFULLY_UNIQUE_VAR: run_with_profile})

        # Run the code.
        #
        # We use a template that does the Fil setup inside the cell, rather
        # than here, so as to keep a whole pile of irrelevant IPython code
        # appearing as frames at the top of the memory profile flamegraph.
        #
        # Empirically inconsistent indents are just fine as far as Python is
        # concerned(?!), so we don't need to do anything special for code that
        # isn't 4-space indented.
        self.shell.run_cell(TEMPLATE.format(indent(cell, "    "), HOPEFULLY_UNIQUE_VAR))

        # Uninject run_with_profile:
        self.shell.drop_by_id({HOPEFULLY_UNIQUE_VAR: run_with_profile})


@contextmanager
def run_with_profile():
    """Run some code under Fil, display result."""
    tempdir = "fil-result"
    start_tracing(tempdir)
    with disable_thread_pools():
        try:
            yield
        finally:
            index_html_path = stop_tracing(tempdir)
            svg_path = Path(index_html_path).parent / "peak-memory.svg"
            display(IFrame(svg_path, width="100%", height="600"))
