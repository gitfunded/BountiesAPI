from datetime import datetime, date
import json

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count

from analytics.filters import BountiesTimelineFilter
from .serializers import BountiesTimelineSerializer, TimelineTagSerializer, TokenListSerializer
from .models import BountiesTimeline
from std_bounties.models import Tag, RankedTag
from std_bounties.views import Tokens


class TimelineBounties(APIView):
    def get(self, request):
        queryset = request.query_params.copy()
        since = queryset.get('since', '')
        until = queryset.get('until', datetime.now().date())
        platform = queryset.get('platform', 'all')

        try:
            since_date = datetime.strptime(since, "%Y-%m-%d").date()

            if not isinstance(until, date):
                until_date = datetime.strptime(until, "%Y-%m-%d").date()
            else:
                until_date = until

            if isinstance(since_date, date) and isinstance(until_date, date):
                queryset['until'] = until_date
                queryset['since'] = since_date

                bounties_timeline = BountiesTimelineFilter(
                    queryset, BountiesTimeline.objects.all().order_by('date'), request=request)

                serialized = BountiesTimelineSerializer(
                    bounties_timeline.qs, many=True, context={
                        'request': request})

                if platform == 'all':
                    ranked_tag_list = RankedTag.objects.distinct().values('normalized_name', 'name')
                    ranked_tags = dict(map(lambda x: (x['normalized_name'], x['name']), ranked_tag_list))

                    gitcoinQuery = Tag.objects.select_related('bounty').filter(
                        bounty__bounty_created__gte=since_date,
                        bounty__bounty_created__lte=until_date,
                        bounty__platform__exact='gitcoin'
                    ).distinct().exclude(normalized_name__exact='').values('normalized_name').annotate(total=Count('bounty'))

                    standardQuery = Tag.objects.select_related('bounty').filter(
                        bounty__bounty_created__gte=since_date,
                        bounty__bounty_created__lte=until_date,
                        bounty__platform__exact='bounties-network'
                    ).distinct().exclude(normalized_name__exact='').values('normalized_name').annotate(total=Count('bounty'))

                    queryset = gitcoinQuery | standardQuery

                else:
                    ranked_tag_list = RankedTag.objects.distinct().values('normalized_name', 'name')
                    ranked_tags = dict(map(lambda x: (x['normalized_name'], x['name']), ranked_tag_list))
                    queryset = Tags.objects.select_related('bounty').filter(
                        bounty__bounty_created__gte=since_date,
                        bounty__bounty_created__lte=until_date,
                        bounty__platform__exact=platform
                    ).distinct().exclude(normalized_name__exact='').values('normalized_name').annotate(total=Count('bounty'))

                tags = TimelineTagSerializer(queryset, many=True, context={'ranked_tags': ranked_tags})

                token_list = json.loads(Tokens.get(self, request).getvalue())
                tokens = TokenListSerializer(token_list, many=True)

                data = {
                    'timeline': serialized.data,
                    'tags': tags.data,
                    'tokens': tokens.data
                }

                return Response(data)

        except ValueError:
            pass

        res = {
            "error": 400,
            "message": "The fields since & until needs being formated as YYYY-MM-DD"}
        return Response(json.dumps(res), status=status.HTTP_200_OK)
