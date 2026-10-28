import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ==============================================================================
# 1. CÁLCULO DE LEY DE CORTE (CUT-OFF GRADE)
# ==============================================================================
def calcular_ley_corte(costo_proceso, costo_ga, precio_cu, costo_venta_gv, recuperacion):
    """
    Calcula la Ley de Corte Crítica / Marginal (% Cu)
    Fórmula: (Costo Proceso + G&A) / [(Precio - Venta) * Rec]
    """
    precio_neto_usd_t = precio_cu - costo_venta_gv
    if precio_neto_usd_t <= 0 or recuperacion <= 0:
        return 0.0
    
    # Costo por tonelada dividido entre el valor neto por punto de ley
    ley_corte_fraccion = (costo_proceso + costo_ga) / (precio_neto_usd_t * (recuperacion / 100.0))
    return ley_corte_fraccion * 100.0  # Retorna en %


# ==============================================================================
# 2. REGALÍA MINERA SEGÚN LEY 29788 (PERÚ)
# ==============================================================================
def calcular_regalia_peru(uo, ingresos):
    if uo <= 0 or ingresos <= 0:
        return ingresos * 0.01
    
    mo = uo / ingresos
    tramos = [
        (0.00, 0.10, 0.0100), (0.10, 0.15, 0.0175), (0.15, 0.20, 0.0250),
        (0.20, 0.25, 0.0325), (0.25, 0.30, 0.0400), (0.30, 0.35, 0.0475),
        (0.35, 0.40, 0.0550), (0.40, 0.45, 0.0625), (0.45, 0.50, 0.0700),
        (0.50, 0.55, 0.0775), (0.55, 0.60, 0.0850), (0.60, 0.65, 0.0925),
        (0.65, 0.70, 0.1000), (0.70, 0.75, 0.1075), (0.75, 0.80, 0.1150),
        (0.80, 0.85, 0.1225), (0.85, 9.99, 0.1200)
    ]
    
    suma_num = 0
    for li, ls, tmg in tramos:
        if mo > ls:
            suma_num += (ls - li) * tmg
        elif mo > li:
            suma_num += (mo - li) * tmg
            break
            
    tasa_efectiva = suma_num / mo
    return max(uo * tasa_efectiva, ingresos * 0.01)


# ==============================================================================
# 3. EVALUACIÓN FINANCIERA COMPLETA CASO BASE (POST-TAX PERÚ)
# ==============================================================================
def evaluar_caso_base(df_lom, capex_m, precio_cu, cm_unit, cp_unit, rec_cu, tasa_desc):
    capex_usd = capex_m * 1e6
    rec_frac = rec_cu / 100.0
    tasa_frac = tasa_desc / 100.0
    costo_venta_gv = 650.0

    flujos_netos = [-capex_usd]
    acumulado_nominal = -capex_usd
    payback_logrado = False
    filas_detalle = []

    for idx, fila in df_lom.iterrows():
        t = fila['Año']
        cm = fila['Total_Rock_t'] * cm_unit
        cp = fila['Tonelaje_RTYPE22_t'] * cp_unit
        cur = fila['Tonelaje_RTYPE22_t'] * (fila['Ley_CU_22'] / 100.0) * rec_frac
        ingresos = cur * (precio_cu - costo_venta_gv)
        
        ebitda = ingresos - cm - cp
        depreciacion = (capex_usd * 0.20) if t <= 5 else 0.0
        ebit = max(0, ebitda - depreciacion)
        
        regalia = calcular_regalia_peru(ebit, ingresos)
        
        # Payback para liberar utilidades PTU (8%)
        flujo_previo = ebitda - regalia
        acumulado_nominal += flujo_previo
        if acumulado_nominal >= 0:
            payback_logrado = True
            
        ptu = max(0, ebit - regalia) * 0.08 if payback_logrado else 0.0
        base_ir = max(0, ebit - regalia - ptu)
        ir = base_ir * 0.295
        
        fcn = ebitda - regalia - ptu - ir
        flujos_netos.append(fcn)
        
        filas_detalle.append({
            'Año': int(t),
            'Ingresos (M$)': ingresos / 1e6,
            'EBITDA (M$)': ebitda / 1e6,
            'Depreciación (M$)': depreciacion / 1e6,
            'Regalía (M$)': regalia / 1e6,
            'PTU 8% (M$)': ptu / 1e6,
            'IR 29.5% (M$)': ir / 1e6,
            'Flujo Neto (M$)': fcn / 1e6
        })

    # VAN
    van = sum(cf / (1 + tasa_frac)**t for t, cf in enumerate(flujos_netos))

    # TIR (Bisección)
    inf, sup = -0.99, 5.0
    for _ in range(80):
        tir = (inf + sup) / 2
        npv_test = sum(cf / (1 + tir)**t for t, cf in enumerate(flujos_netos))
        if abs(npv_test) < 1e-2:
            break
        if npv_test > 0:
            inf = tir
        else:
            sup = tir

    # Payback Descontado
    acum_desc = 0
    prd = 0
    for t, cf in enumerate(flujos_netos):
        cf_d = cf / (1 + tasa_frac)**t
        if t == 0:
            acum_desc = cf_d
            continue
        prev = acum_desc
        acum_desc += cf_d
        if prev < 0 and acum_desc >= 0:
            prd = (t - 1) + (abs(prev) / cf_d)
            break

    return {
        'VAN_M': van / 1e6,
        'TIR': tir * 100.0,
        'PRD': prd,
        'tabla': pd.DataFrame(filas_detalle)
    }


# ==============================================================================
# 4. SIMULACIÓN DE MONTECARLO (10,000 ITERACIONES VECTORIZADAS)
# ==============================================================================
def correr_montecarlo(df_lom, capex_m, precio_cu_base, cm_base, cp_base, rec_cu_base, tasa_desc, n_sim=5000):
    tasa_frac = tasa_desc / 100.0
    costo_venta_gv = 650.0
    
    np.random.seed(42)
    # Generar variables aleatorias
    precios_cu = np.random.normal(loc=precio_cu_base, scale=1000, size=n_sim)
    costos_m = np.random.normal(loc=cm_base, scale=0.25, size=n_sim)
    costos_p = np.random.normal(loc=cp_base, scale=0.8, size=n_sim)
    recs_cu = np.random.normal(loc=rec_cu_base / 100.0, scale=0.02, size=n_sim)
    capexs = np.random.normal(loc=capex_m * 1e6, scale=75e6, size=n_sim)
    
    # Extraer arrays numpy para velocidad máxima (< 1 seg)
    anios = df_lom['Año'].values
    rock = df_lom['Total_Rock_t'].values
    ore = df_lom['Tonelaje_RTYPE22_t'].values
    ley = (df_lom['Ley_CU_22'].values / 100.0)
    
    factores_desc = 1.0 / ((1.0 + tasa_frac) ** anios)
    
    van_resultados = np.zeros(n_sim)
    
    for s in range(n_sim):
        p = precios_cu[s]
        cm_u = costos_m[s]
        cp_u = costos_p[s]
        rec_u = recs_cu[s]
        cap = capexs[s]
        
        cm_anual = rock * cm_u
        cp_anual = ore * cp_u
        cur_anual = ore * ley * rec_u
        ingresos_anual = cur_anual * (p - costo_venta_gv)
        ebitda_anual = ingresos_anual - cm_anual - cp_anual
        
        # Depreciación acelerada simplificada para velocidad en simulación
        dep_anual = np.where(anios <= 5, cap * 0.20, 0.0)
        ebit_anual = np.maximum(0, ebitda_anual - dep_anual)
        
        # Regalía aproximada rápida (media ~5%) e Impuestos
        mo_anual = np.where(ingresos_anual > 0, ebit_anual / ingresos_anual, 0)
        tasa_regalia = np.clip(mo_anual * 0.08, 0.01, 0.065)
        regalia_anual = ebit_anual * tasa_regalia
        
        ir_anual = np.maximum(0, ebit_anual - regalia_anual) * 0.295
        fcn_anual = ebitda_anual - regalia_anual - ir_anual
        
        van_resultados[s] = np.sum(fcn_anual * factores_desc) - cap

    van_m = van_resultados / 1e6
    p10 = float(np.percentile(van_m, 10))
    p50 = float(np.percentile(van_m, 50))
    p90 = float(np.percentile(van_m, 90))
    prob_exito = float((van_m > 0).mean() * 100.0)

    # Gráfico Matplotlib para mostrar en Streamlit
    fig, ax = plt.subplots(figsize=(10, 4.5))
    sns.set_style("white")
    sns.histplot(van_m, kde=True, color='teal', bins=60, edgecolor='black', alpha=0.6, ax=ax)
    
    ax.axvline(p10, color='red', linestyle='--', linewidth=2, label=f'P10 Pesimista: {p10:,.1f} M$')
    ax.axvline(p50, color='green', linestyle='-.', linewidth=2, label=f'P50 Mediana: {p50:,.1f} M$')
    ax.axvline(p90, color='orange', linestyle=':', linewidth=2, label=f'P90 Optimista: {p90:,.1f} M$')
    
    ax.set_title('Distribución de Riesgo del VAN (Simulación Montecarlo)', fontsize=13, fontweight='bold')
    ax.set_xlabel('VAN Neto (Millones de USD)')
    ax.set_ylabel('Frecuencia')
    ax.legend()
    ax.grid(True, linestyle=':', alpha=0.5)
    plt.tight_layout()

    return {
        'P10': p10,
        'P50': p50,
        'P90': p90,
        'prob_exito': prob_exito,
        'figura': fig
    }