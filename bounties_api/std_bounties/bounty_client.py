import json
import datetime
from decimal import Decimal
from std_bounties.models import Fulfillment, DraftBounty
from std_bounties.serializers import BountySerializer, ContributionSerializer, FulfillmentSerializer
from std_bounties.constants import DRAFT_STAGE, ACTIVE_STAGE, DEAD_STAGE, COMPLETED_STAGE, EXPIRED_STAGE
from std_bounties.client_helpers import map_bounty_data, map_token_data, map_fulfillment_data, get_token_pricing, get_historic_pricing
from user.models import User
from bounties.utils import getDateTimeFromTimestamp
from django.db import transaction
import logging


logger = logging.getLogger('django')

issue_bounty_input_keys = [
    'fulfillmentAmount',
    'arbiter',
    'paysTokens',
    'tokenContract',
    'value']


class BountyClient:

    def __init__(self):
        pass

    @transaction.atomic
    def issue_bounty(self, bounty_id, contract_version, **kwargs):
        event_date = datetime.datetime.fromtimestamp(int(kwargs.get('event_timestamp')))

        ipfs_data = map_bounty_data(kwargs.get('data', ''), bounty_id)
        token_data = map_token_data(kwargs.get('token_version'), kwargs.get('token'), 0)

        # TODO what happens if issuers or approvers is actually blank?
        contract_state = {'issuers': {}, 'approvers': {}}
        issuers = []
        for index, issuer in enumerate(kwargs.get('issuers', [])):
            user = User.objects.get_or_create(public_address=issuer.lower())[0]
            issuers.append(user.pk)
            contract_state['issuers'].update({issuer: index})

        approvers = []
        for index, approver in enumerate(kwargs.get('approvers', [])):
            user = User.objects.get_or_create(public_address=approver.lower())[0]
            approvers.append(user.pk)
            contract_state['approvers'].update({approver: index})

        bounty_data = {
            'bounty_id': bounty_id,
            'contract_version': contract_version,

            # legacy for stb 1.0
            'user': issuers[0],
            'issuer': kwargs.get('issuers')[0],
            ###

            'issuers': issuers,
            'approvers': approvers,
            'contract_state': json.dumps(contract_state),
            'deadline': getDateTimeFromTimestamp(kwargs.get('deadline', None)),
            'bounty_stage': DEAD_STAGE,
            'bounty_created': event_date,
        }

        bounty_serializer = BountySerializer(data={
            **bounty_data,
            **ipfs_data,
            **token_data
        })

        bounty_serializer.is_valid(raise_exception=True)

        saved_bounty = bounty_serializer.save()
        saved_bounty.save_and_clear_categories(ipfs_data.get('data_categories'))
        saved_bounty.record_bounty_state(event_date)

        uid = saved_bounty.uid

        if uid:
            DraftBounty.objects.filter(uid=uid).update(on_chain=True)

        return saved_bounty

    def activate_bounty(self, bounty, inputs, event_timestamp, **kwargs):
        event_date = datetime.datetime.fromtimestamp(int(event_timestamp))
        bounty.bountyStage = ACTIVE_STAGE
        bounty.record_bounty_state(event_date)
        bounty.save()

        return bounty

    def fulfill_bounty(self, bounty, **kwargs):
        fulfillment_id = kwargs.get('fulfillment_id')

        fulfillment = Fulfillment.objects.filter(
            fulfillment_id=fulfillment_id,
            bounty_id=bounty.bounty_id,
            contract_version=bounty.contract_version,
        )

        if fulfillment.exists():
            return

        data_hash = kwargs.get('data')
        ipfs_data = map_fulfillment_data(data_hash, bounty.bounty_id, fulfillment_id)

        fulfillment_data = {
            'contract_version': bounty.contract_version,
            'fulfillment_id': fulfillment_id,
            'fulfiller': kwargs.get('fulfillers')[0],
            'bounty': bounty.id,
            'accepted': False,
            'fulfillment_created': datetime.datetime.fromtimestamp(int(kwargs.get('event_timestamp'))),
        }

        fulfillment_serializer = FulfillmentSerializer(data={
            **fulfillment_data,
            **ipfs_data
        })

        fulfillment_serializer.is_valid(raise_exception=True)

        return fulfillment_serializer.save()

    def update_fulfillment(self, bounty, fulfillment_id, inputs, **kwargs):
        fulfillment = Fulfillment.objects.get(
            fulfillment_id=fulfillment_id, bounty_id=bounty.bounty_id)

        data_hash = inputs.get('data')
        ipfs_data = map_fulfillment_data(
            data_hash, bounty.bounty_id, fulfillment_id)

        fulfillment_serializer = FulfillmentSerializer(
            fulfillment, data={**ipfs_data}, partial=True)
        instance = fulfillment_serializer.save()

        return instance

    @transaction.atomic
    def accept_fulfillment(self, bounty, **kwargs):
        event_date = datetime.datetime.fromtimestamp(int(kwargs.get('event_timestamp')))
        bounty.balance = bounty.balance - bounty.fulfillment_amount

        usd_price, token_price = get_historic_pricing(
            bounty.token_symbol,
            bounty.token_decimals,
            bounty.fulfillment_amount,
            kwargs.get('event_timestamp')
        )

        if bounty.balance < bounty.fulfillment_amount:
            bounty.bounty_stage = COMPLETED_STAGE
            bounty.usd_price = usd_price
            bounty.token_lock_price = token_price
            bounty.record_bounty_state(event_date)

        bounty.save()

        fulfillment = Fulfillment.objects.get(bounty=bounty.pk, fulfillment_id=kwargs.get('fulfillment_id'))
        fulfillment.accepted = True
        fulfillment.usd_price = usd_price
        fulfillment.accepted_date = getDateTimeFromTimestamp(kwargs.get('event_timestamp'))
        fulfillment.save()

        return fulfillment

    def kill_bounty(self, bounty, event_timestamp, **kwargs):
        event_date = datetime.datetime.fromtimestamp(int(event_timestamp))
        bounty.old_balance = bounty.balance
        bounty.balance = 0
        usd_price, token_price = get_historic_pricing(
            bounty.tokenSymbol,
            bounty.tokenDecimals,
            bounty.fulfillmentAmount,
            event_timestamp)
        has_accepted_fulfillments = bounty.fulfillments.filter(
            accepted=True).exists()
        if has_accepted_fulfillments:
            bounty.bountyStage = COMPLETED_STAGE
        else:
            bounty.bountyStage = DEAD_STAGE
        bounty.usd_price = usd_price
        bounty.tokenLockPrice = token_price
        bounty.record_bounty_state(event_date)
        bounty.save()

        return bounty

    def add_contribution(self, bounty, **kwargs):
        event_date = datetime.datetime.fromtimestamp(int(kwargs.get('event_timestamp')))
        bounty.balance = Decimal(bounty.balance) + Decimal(kwargs.get('value', kwargs.get('amount')))

        # not sure about this ... what if the bounty expired because the deadline passed?
        if bounty.balance >= bounty.fulfillment_amount and bounty.bounty_stage == EXPIRED_STAGE:
            bounty.bounty_stage = ACTIVE_STAGE
            bounty.record_bounty_state(event_date)

        if bounty.balance >= bounty.fulfillment_amount and bounty.bounty_stage == COMPLETED_STAGE:
            bounty.bountyStage = ACTIVE_STAGE
            bounty.record_bounty_state(event_date)
            bounty.usd_price = get_token_pricing(
                bounty.token_symbol,
                bounty.token_decimals,
                bounty.fulfillment_amount
            )[0]

        bounty.save()

        contribution_serializer = ContributionSerializer(data={
            'contributor': User.objects.get_or_create(public_address=kwargs.get('contributor'))[0].pk,
            'bounty': bounty.pk,
            'contribution_id': kwargs.get('contribution_id'),
            'amount': kwargs.get('amount'),
            # 'raw_event_data': json.dumps(kwargs),
        })

        contribution_serializer.is_valid(raise_exception=True)
        contribution = contribution_serializer.save()

        return contribution

    def change_deadline(self, bounty, **kwargs):
        event_date = datetime.datetime.fromtimestamp(int(kwargs.get('event_timestamp')))
        bounty.deadline = getDateTimeFromTimestamp(kwargs.get('deadline'))

        if bounty.deadline > datetime.datetime.now() and bounty.bounty_stage == EXPIRED_STAGE:
            bounty.bounty_stage = ACTIVE_STAGE
            bounty.record_bounty_state(event_date)
        elif bounty.deadline < datetime.datetime.now() and bounty.bounty_stage == ACTIVE_STAGE:
            bounty.bounty_stage = EXPIRED_STAGE
            bounty.record_bounty_state(event_date)

        bounty.save()

        return bounty

    @transaction.atomic
    def change_bounty(self, bounty, inputs, **kwargs):
        updated_data = {}
        data_hash = inputs.get('newData', None) or inputs.get('data', None)
        deadline = inputs.get('newDeadline', None)
        fulfillmentAmount = inputs.get('newFulfillmentAmount', None)
        arbiter = inputs.get('newArbiter', None)

        if data_hash:
            updated_data = map_bounty_data(data_hash, bounty.bounty_id)

        if deadline:
            updated_data['deadline'] = datetime.datetime.fromtimestamp(
                int(deadline))

        if fulfillmentAmount:
            updated_data['fulfillmentAmount'] = Decimal(fulfillmentAmount)

        if arbiter:
            updated_data['arbiter'] = arbiter

        bounty_serializer = BountySerializer(
            bounty, data=updated_data, partial=True)
        bounty_serializer.is_valid(raise_exception=True)
        saved_bounty = bounty_serializer.save()

        if data_hash:
            saved_bounty.save_and_clear_categories(
                updated_data.get('data_categories'))

        if fulfillmentAmount:
            usd_price = get_token_pricing(
                saved_bounty.tokenSymbol,
                saved_bounty.tokenDecimals,
                fulfillmentAmount)[0]
            saved_bounty.usd_price = usd_price
            saved_bounty.save()

        return saved_bounty

    def transfer_issuer(self, bounty, inputs, **kwargs):
        bounty.issuer = inputs.get('newIssuer')
        bounty.save()

        return bounty

    def increase_payout(self, bounty, inputs, **kwargs):
        value = inputs.get('value')
        fulfillment_amount = inputs.get('newFulfillmentAmount')
        if value:
            bounty.balance = bounty.balance + Decimal(value)
        usd_price = get_token_pricing(
            bounty.tokenSymbol,
            bounty.tokenDecimals,
            fulfillment_amount)[0]
        bounty.fulfillmentAmount = Decimal(fulfillment_amount)
        bounty.usd_price = usd_price
        bounty.save()

        return bounty
