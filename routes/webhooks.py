from flask import Blueprint, request, jsonify
from database.models import db, WebhookLog, PedidoLogistica
from services.mandae_service import MandaeService
from datetime import datetime

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')


@webhooks_bp.route('/mandae', methods=['POST'])
def webhook_mandae():
    """
    POST /api/webhooks/mandae
    Webhook do evento 'item processado' da Mandaê.
    Header: X-Mandae-Signature (opcional, para validar assinatura)
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({'erro': 'Payload JSON obrigatório'}), 400

        assinatura = request.headers.get('X-Mandae-Signature')
        if assinatura and not MandaeService.validar_webhook(payload, assinatura):
            return jsonify({'erro': 'Assinatura inválida'}), 401

        webhook_log = WebhookLog(
            origem='mandae',
            payload=payload,
            status_processamento='pendente',
            numero_pedido=payload.get('partnerItemId')
        )
        db.session.add(webhook_log)
        db.session.commit()

        processar_webhook_mandae(payload, webhook_log.id)

        return jsonify({'status': 'recebido'}), 202

    except Exception as e:
        print(f"Erro ao processar webhook Mandaê: {str(e)}")
        return jsonify({'erro': str(e)}), 500


@webhooks_bp.route('/bling', methods=['POST'])
def webhook_bling():
    """POST /api/webhooks/bling - Webhook de novos pedidos ou atualizações do Bling."""
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({'erro': 'Payload JSON obrigatório'}), 400

        webhook_log = WebhookLog(
            origem='bling',
            payload=payload,
            status_processamento='pendente'
        )
        db.session.add(webhook_log)
        db.session.commit()

        processar_webhook_bling(payload, webhook_log.id)

        return jsonify({'status': 'recebido'}), 202

    except Exception as e:
        print(f"Erro ao processar webhook Bling: {str(e)}")
        return jsonify({'erro': str(e)}), 500


def processar_webhook_mandae(payload, webhook_log_id):
    """Processar payload do webhook Mandaê."""
    try:
        partner_item_id = payload.get('partnerItemId')
        tracking_code = payload.get('trackingCode')
        webhook = WebhookLog.query.get(webhook_log_id)
        if not webhook:
            return

        pedido = PedidoLogistica.query.filter_by(id_bling=str(partner_item_id)).first()

        if pedido:
            pedido.tracking_code = tracking_code
            webhook.status_processamento = 'processado'
            webhook.processado_em = datetime.utcnow()
            db.session.commit()
        else:
            webhook.status_processamento = 'erro'
            webhook.mensagem_erro = f"Pedido com ID Bling {partner_item_id} não encontrado"
            db.session.commit()

    except Exception as e:
        webhook = WebhookLog.query.get(webhook_log_id)
        if webhook:
            webhook.status_processamento = 'erro'
            webhook.mensagem_erro = str(e)
            db.session.commit()
        print(f"Erro ao processar webhook Mandaê: {str(e)}")


def processar_webhook_bling(payload, webhook_log_id):
    """Processar payload do webhook Bling (estrutura conforme documentação Bling)."""
    try:
        webhook = WebhookLog.query.get(webhook_log_id)
        if webhook:
            webhook.status_processamento = 'processado'
            webhook.processado_em = datetime.utcnow()
            db.session.commit()
    except Exception as e:
        webhook = WebhookLog.query.get(webhook_log_id)
        if webhook:
            webhook.status_processamento = 'erro'
            webhook.mensagem_erro = str(e)
            db.session.commit()
        print(f"Erro ao processar webhook Bling: {str(e)}")
