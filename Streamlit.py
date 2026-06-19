import random
import streamlit as st
import sympy as sp

st.set_page_config(page_title="Generador y solucionador de álgebra", layout="centered")

x = sp.symbols('x')

def generate_linear():
    a = random.randint(-10, 10)
    while a == 0:
        a = random.randint(-10, 10)
    b = random.randint(-20, 20)
    return {"type": "linear", "a": a, "b": b}

def generate_quadratic():
    a = random.randint(-5, 5)
    while a == 0:
        a = random.randint(-5, 5)
    b = random.randint(-10, 10)
    c = random.randint(-10, 10)
    return {"type": "quadratic", "a": a, "b": b, "c": c}

def solve_linear(a, b):
    sol = sp.solve(sp.Eq(a*x + b, 0), x)
    return sol

def linear_steps_latex(a, b, sol):
    eq_latex = sp.latex(sp.Eq(a*x + b, 0))
    sol_latex = sp.latex(sp.Eq(x, sp.simplify(sol[0])))
    steps = r"%s \quad \Rightarrow \quad %s" % (eq_latex, sol_latex)
    return steps

def solve_quadratic(a, b, c):
    sols = sp.solve(sp.Eq(a*x**2 + b*x + c, 0), x)
    return sols

def quadratic_steps_latex(a, b, c, sols):
    eq_latex = sp.latex(sp.Eq(a*x**2 + b*x + c, 0))
    D = b**2 - 4*a*c
    disc_latex = sp.latex(sp.Eq(sp.Symbol("D"), sp.simplify(D)))
    formula_latex = r"x = \frac{-%s \pm \sqrt{%s}}{2 \cdot %s}" % (sp.latex(b), sp.latex(D), sp.latex(a))
    sols_latex = ",\\; ".join(sp.latex(s) for s in sols)
    steps = (
        eq_latex
        + r"\\[6pt]"
        + r"\text{Discriminante: }" + disc_latex
        + r"\\[6pt]"
        + r"\text{Fórmula: }" + formula_latex
        + r"\\[6pt]"
        + r"\text{Soluciones: }" + sols_latex
    )
    return steps

st.title("Generador y solucionador de álgebra")
st.write("Genera y resuelve ecuaciones lineales y cuadráticas. Usa la casilla 'Mostrar pasos' para ver razonamiento simbólico.")

with st.sidebar:
    st.header("Opciones")
    problem_type = st.selectbox("Tipo de problema", ["aleatorio", "lineal", "cuadrática"])
    show_steps = st.checkbox("Mostrar pasos", value=True)
    st.markdown("---")
    st.markdown("Puedes introducir tus propios coeficientes abajo y pulsar 'Resolver manual'.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Generar problema")
    if st.button("Generar"):
        if problem_type == "lineal":
            prob = generate_linear()
        elif problem_type == "cuadrática":
            prob = generate_quadratic()
        else:
            prob = random.choice([generate_linear(), generate_quadratic()])
        st.session_state["last_problem"] = prob

    if "last_problem" in st.session_state:
        prob = st.session_state["last_problem"]
        if prob["type"] == "linear":
            a, b = prob["a"], prob["b"]
            st.markdown("Problema (ecuación lineal):")
            st.latex(sp.Eq(a*x + b, 0))
            sols = solve_linear(a, b)
            if show_steps:
                st.markdown("Pasos:")
                st.latex(linear_steps_latex(a, b, sols))
            st.markdown("Solución:")
            for s in sols:
                st.latex(sp.Eq(x, sp.simplify(s)))
        else:
            a, b, c = prob["a"], prob["b"], prob["c"]
            st.markdown("Problema (ecuación cuadrática):")
            st.latex(sp.Eq(a*x**2 + b*x + c, 0))
            sols = solve_quadratic(a, b, c)
            if show_steps:
                st.markdown("Pasos:")
                st.latex(quadratic_steps_latex(a, b, c, sols))
            st.markdown("Soluciones:")
            for s in sols:
                st.latex(sp.Eq(x, sp.simplify(s)))

with col2:
    st.subheader("Resolver manual")
    st.write("Introduce coeficientes y pulsa el botón.")
    form = st.form(key="manual_form")
    choice = form.selectbox("Tipo", ["lineal", "cuadrática"])
    if choice == "lineal":
        a_in = form.number_input("a (no puede ser 0)", value=1, step=1)
        b_in = form.number_input("b", value=0, step=1)
    else:
        a_in = form.number_input("a (no puede ser 0)", value=1, step=1)
        b_in = form.number_input("b", value=0, step=1)
        c_in = form.number_input("c", value=0, step=1)
    submitted = form.form_submit_button("Resolver manual")
    if submitted:
        try:
            a_val = int(a_in)
            if a_val == 0:
                st.error("El coeficiente 'a' no puede ser 0.")
            else:
                if choice == "lineal":
                    sols = solve_linear(a_val, int(b_in))
                    st.markdown("Ecuación:")
                    st.latex(sp.Eq(a_val*x + int(b_in), 0))
                    if show_steps:
                        st.markdown("Pasos:")
                        st.latex(linear_steps_latex(a_val, int(b_in), sols))
                    st.markdown("Solución:")
                    for s in sols:
                        st.latex(sp.Eq(x, sp.simplify(s)))
                    st.session_state["last_problem"] = {"type": "linear", "a": a_val, "b": int(b_in)}
                else:
                    sols = solve_quadratic(a_val, int(b_in), int(c_in))
                    st.markdown("Ecuación:")
                    st.latex(sp.Eq(a_val*x**2 + int(b_in)*x + int(c_in), 0))
                    if show_steps:
                        st.markdown("Pasos:")
                        st.latex(quadratic_steps_latex(a_val, int(b_in), int(c_in), sols))
                    st.markdown("Soluciones:")
                    for s in sols:
                        st.latex(sp.Eq(x, sp.simplify(s)))
                    st.session_state["last_problem"] = {"type": "quadratic", "a": a_val, "b": int(b_in), "c": int(c_in)}
        except Exception as e:
            st.error(f"Error al resolver: {e}")

st.markdown("---")
st.write("Sugerencias: puedes ampliar esta app para generar listas de ejercicios, exportar a CSV/PDF, o añadir tipos adicionales (sistemas, factorización, inecuaciones).")
