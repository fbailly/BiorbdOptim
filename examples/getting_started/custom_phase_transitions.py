"""
This example is a trivial multiphase box that must superimpose different markers at beginning and end of each
phase with one of its corner
It is designed to show how one can define its phase transition constraints if the provided ones are not sufficient.

More specifically, this example mimics the behaviour of the most common StateTransitionFcn.CONTINUOUS
"""

from casadi import MX
import biorbd
from bioptim import (
    Node,
    OptimalControlProgram,
    DynamicsFcn,
    DynamicsList,
    ObjectiveFcn,
    ObjectiveList,
    ConstraintFcn,
    ConstraintList,
    BoundsList,
    QAndQDotBounds,
    InitialGuessList,
    StateTransitionFcn,
    StateTransitionList,
    ShowResult,
    OdeSolver,
)


def custom_state_transition(state_pre: MX, state_post: MX, idx_1: int, idx_2: int) -> MX:
    """
    The constraint of the transition. if idx_1 is the first state and idx_2 is the last, this function mimics the
    StateTransitionFcn.CONTINUOUS. idx_1 and idx_2 are user defined extra variables and can be anything

    Parameters
    ----------
    state_pre: MX
        The states at the end of a phase
    state_post: MX
        The state at the beginning of the next phase
    idx_1: int
        The state first index of the slicing of the states
    idx_2: int
        The state last index of the slicing of the states

    Returns
    -------
    The constraint such that: c(x) = 0
    """

    return state_pre[idx_1:idx_2] - state_post[idx_1:idx_2]


def prepare_ocp(biorbd_model_path: str = "cube.bioMod", ode_solver: OdeSolver = OdeSolver.RK4) -> OptimalControlProgram:
    """
    Parameters
    ----------
    biorbd_model_path: str
        The path to the bioMod
    ode_solver: OdeSolver
        The type of ode solver used

    Returns
    -------
    The ocp ready to be solved
    """

    # Model path
    biorbd_model = (
        biorbd.Model(biorbd_model_path),
        biorbd.Model(biorbd_model_path),
        biorbd.Model(biorbd_model_path),
        biorbd.Model(biorbd_model_path),
    )

    # Problem parameters
    n_shooting = (20, 20, 20, 20)
    final_time = (2, 5, 4, 2)
    tau_min, tau_max, tau_init = -100, 100, 0

    # Add objective functions
    objective_functions = ObjectiveList()
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_TORQUE, weight=100, phase=0)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_TORQUE, weight=100, phase=1)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_TORQUE, weight=100, phase=2)
    objective_functions.add(ObjectiveFcn.Lagrange.MINIMIZE_TORQUE, weight=100, phase=3)

    # Dynamics
    dynamics = DynamicsList()
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)
    dynamics.add(DynamicsFcn.TORQUE_DRIVEN)

    # Constraints
    constraints = ConstraintList()
    constraints.add(
        ConstraintFcn.SUPERIMPOSE_MARKERS, node=Node.START, first_marker_idx=0, second_marker_idx=1, phase=0
    )
    constraints.add(ConstraintFcn.SUPERIMPOSE_MARKERS, node=Node.END, first_marker_idx=0, second_marker_idx=2, phase=0)
    constraints.add(ConstraintFcn.SUPERIMPOSE_MARKERS, node=Node.END, first_marker_idx=0, second_marker_idx=1, phase=1)
    constraints.add(ConstraintFcn.SUPERIMPOSE_MARKERS, node=Node.END, first_marker_idx=0, second_marker_idx=2, phase=2)
    constraints.add(ConstraintFcn.SUPERIMPOSE_MARKERS, node=Node.END, first_marker_idx=0, second_marker_idx=1, phase=3)

    # Path constraint
    x_bounds = BoundsList()
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))
    x_bounds.add(bounds=QAndQDotBounds(biorbd_model[0]))

    x_bounds[0][[1, 3, 4, 5], 0] = 0
    x_bounds[-1][[1, 3, 4, 5], -1] = 0

    x_bounds[0][2, 0] = 0.0
    x_bounds[2][2, [0, -1]] = [0.0, 1.57]

    # Initial guess
    x_init = InitialGuessList()
    x_init.add([0] * (biorbd_model[0].nbQ() + biorbd_model[0].nbQdot()))
    x_init.add([0] * (biorbd_model[0].nbQ() + biorbd_model[0].nbQdot()))
    x_init.add([0] * (biorbd_model[0].nbQ() + biorbd_model[0].nbQdot()))
    x_init.add([0] * (biorbd_model[0].nbQ() + biorbd_model[0].nbQdot()))

    # Define control path constraint
    u_bounds = BoundsList()
    u_bounds.add([tau_min] * biorbd_model[0].nbGeneralizedTorque(), [tau_max] * biorbd_model[0].nbGeneralizedTorque())
    u_bounds.add([tau_min] * biorbd_model[0].nbGeneralizedTorque(), [tau_max] * biorbd_model[0].nbGeneralizedTorque())
    u_bounds.add([tau_min] * biorbd_model[0].nbGeneralizedTorque(), [tau_max] * biorbd_model[0].nbGeneralizedTorque())
    u_bounds.add([tau_min] * biorbd_model[0].nbGeneralizedTorque(), [tau_max] * biorbd_model[0].nbGeneralizedTorque())

    u_init = InitialGuessList()
    u_init.add([tau_init] * biorbd_model[0].nbGeneralizedTorque())
    u_init.add([tau_init] * biorbd_model[0].nbGeneralizedTorque())
    u_init.add([tau_init] * biorbd_model[0].nbGeneralizedTorque())
    u_init.add([tau_init] * biorbd_model[0].nbGeneralizedTorque())

    """
    By default, all state transitions (here phase 0 to phase 1, phase 1 to phase 2 and phase 2 to phase 3)
    are continuous. In the event that one (or more) state transition(s) is desired to be discontinuous,
    as for example IMPACT or CUSTOM can be used as below.
    "phase_pre_idx" corresponds to the index of the phase preceding the transition.
    IMPACT will cause an impact related discontinuity when defining one or more contact points in the model.
    CUSTOM will allow to call the custom function previously presented in order to have its own state transition.
    Finally, if you want a state transition (continuous or not) between the last and the first phase (cyclicity)
    you can use the dedicated StateTransitionFcn.Cyclic or use a continuous set at the lase phase_pre_idx.

    If for some reason, you don't want the state transition to be hard constraint, you can specify a weight higher than
    zero. It will thereafter be treated as a Mayer objective function with the specified weight.
    """
    state_transitions = StateTransitionList()
    state_transitions.add(StateTransitionFcn.IMPACT, phase_pre_idx=1)
    state_transitions.add(custom_state_transition, phase_pre_idx=2, idx_1=1, idx_2=3)
    state_transitions.add(StateTransitionFcn.CYCLIC)

    return OptimalControlProgram(
        biorbd_model,
        dynamics,
        n_shooting,
        final_time,
        x_init,
        u_init,
        x_bounds,
        u_bounds,
        objective_functions,
        constraints,
        ode_solver=ode_solver,
        state_transitions=state_transitions,
    )


if __name__ == "__main__":
    ocp = prepare_ocp()

    # --- Solve the program --- #
    sol = ocp.solve(show_online_optim=True)

    # --- Show results --- #
    result = ShowResult(ocp, sol)
    result.animate()
