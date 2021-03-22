from ..utils import log, CYA, RED, DRED
import angr
from angr import sim_options
from angr.procedures.stubs.format_parser import FormatParser


bits = 128 # should be set to 32 or 64


class PrintfHook(angr.procedures.libc.printf.printf) :
    IS_FUNCTION = True

    def checkFSB(self) :
        fmt_str = self.state.memory.load(self.state.solver.eval(self.arg(0)), size=bits)
        if fmt_str.symbolic :
            log("FSB!", RED)
            return True
        return False

    def run(self) :
        if not self.checkFSB() :
            stdout = self.state.posix.get_fd(1)
            if stdout is None:
                return -1

            # The format str is at index 0
            fmt_str = self._parse(0)
            out_str = fmt_str.replace(1, self.arg)

            stdout.write_data(out_str, out_str.size() // 8)
            return out_str.size() // 8


def check(file_name) :
    log("Checking Format String Bug", CYA)

    try:
        project = angr.Project(file_name, load_options={'auto_load_libs': False})
    except:
        log("Path does not point to a valid binary file: " + file_name + "\n", DRED)
        return

    global bits
    bits = project.arch.bits

    project.hook_symbol('printf',
                        PrintfHook(cc=project.factory.cc(func_ty="int printf(const char *format, ...)")),
                        replace=True)

    extra_option = {sim_options.REVERSE_MEMORY_NAME_MAP,
                    sim_options.TRACK_ACTION_HISTORY}
    init_state = project.factory.entry_state(add_options=extra_option)
    simgr = project.factory.simulation_manager(init_state, veritesting=False, save_unconstrained=True)

    while simgr.active :
        simgr.step()
