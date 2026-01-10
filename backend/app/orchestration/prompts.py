"""Prompt templates for agents (used with LLM providers)."""

# Transaction Context Analysis
CONTEXT_ANALYSIS_PROMPT = """Analiza la siguiente transacción y su contexto:

Transacción:
- ID: {transaction_id}
- Monto: {amount} {currency}
- País: {country}
- Canal: {channel}
- Dispositivo: {device_id}
- Merchant: {merchant_id}
- Timestamp: {timestamp}

Comportamiento usual del cliente:
- Monto promedio: {usual_amount_avg}
- Horario habitual: {usual_hours_start}:00 - {usual_hours_end}:00
- Países habituales: {usual_countries}
- Dispositivos habituales: {usual_devices}

Identifica señales de riesgo comparando la transacción con el comportamiento habitual."""

# Behavioral Pattern Analysis
BEHAVIOR_ANALYSIS_PROMPT = """Basándote en las siguientes métricas, evalúa el nivel de riesgo comportamental:

Métricas:
- Ratio de monto: {amount_ratio}x del promedio
- Hora de transacción: {hour}:00
- Fuera de horario habitual: {hour_outside}
- País nuevo: {new_country}
- Dispositivo nuevo: {new_device}

Proporciona un score de riesgo comportamental entre 0 y 1."""

# Policy RAG Query
POLICY_QUERY_PROMPT = """Busca políticas relevantes para una transacción con las siguientes características:
{signals}

Métricas: {metrics}"""

# Debate Pro-Fraud
DEBATE_PRO_FRAUD_PROMPT = """Como abogado del fraude, argumenta por qué esta transacción podría ser fraudulenta:

Señales detectadas: {signals}
Métricas: {metrics}
Alertas externas: {external_alerts}
Políticas aplicables: {policies}

Proporciona:
1. Tu recomendación de decisión (BLOCK, CHALLENGE, APPROVE)
2. Nivel de confianza adicional (0.0-0.1)
3. Razonamiento"""

# Debate Pro-Customer
DEBATE_PRO_CUSTOMER_PROMPT = """Como abogado del cliente, argumenta por qué esta transacción podría ser legítima:

Señales detectadas: {signals}
Métricas: {metrics}
Historial del cliente: {customer_history}

Proporciona:
1. Tu recomendación de decisión (APPROVE, CHALLENGE)
2. Reducción de confianza sugerida (0.0-0.05)
3. Razonamiento"""

# Arbiter Decision
ARBITER_PROMPT = """Como árbitro, toma la decisión final basándote en:

Señales: {signals}
Métricas: {metrics}
Debate Pro-Fraude: {pro_fraud}
Debate Pro-Cliente: {pro_customer}
Policy Hint: {policy_hint}
Alertas Externas: {external_count}

Decide: APPROVE, CHALLENGE, BLOCK, o ESCALATE_TO_HUMAN
Proporciona nivel de confianza (0.0-1.0) y razonamiento."""

# Explainability
EXPLAIN_CUSTOMER_PROMPT = """Genera una explicación amigable para el cliente sobre la decisión:
Decisión: {decision}
Señales principales: {signals}"""

EXPLAIN_AUDIT_PROMPT = """Genera una explicación técnica para auditoría:
Decisión: {decision}
Confianza: {confidence}
Señales: {signals}
Políticas citadas: {policies}
Alertas externas: {external_alerts}
Ruta de agentes: {agent_route}"""
