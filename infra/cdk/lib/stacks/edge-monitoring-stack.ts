import { Duration, Stack, StackProps } from "aws-cdk-lib";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as sns from "aws-cdk-lib/aws-sns";
import { Construct } from "constructs";

interface EdgeMonitoringStackProps extends StackProps {
  applicationName: string;
  distribution: cloudfront.Distribution;
  environmentName: string;
}

export class EdgeMonitoringStack extends Stack {
  public readonly alertTopic: sns.Topic;

  constructor(scope: Construct, id: string, props: EdgeMonitoringStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    this.alertTopic = new sns.Topic(this, "AlertTopic", {
      topicName: `${resourceNamePrefix}-edge-alerts`,
    });

    const cloudFront5xxErrorRateAlarm = new cloudwatch.Alarm(
      this,
      "CloudFront5xxErrorRateAlarm",
      {
        alarmDescription: "CloudFrontの5xxエラー率が3分間5%以上",
        alarmName: `${resourceNamePrefix}-cloudfront-5xx-error-rate`,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        evaluationPeriods: 3,
        metric: props.distribution.metric5xxErrorRate({
          period: Duration.minutes(1),
          statistic: cloudwatch.Stats.AVERAGE,
        }),
        threshold: 5,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      },
    );

    cloudFront5xxErrorRateAlarm.addAlarmAction(
      new cloudwatchActions.SnsAction(this.alertTopic),
    );
  }
}
