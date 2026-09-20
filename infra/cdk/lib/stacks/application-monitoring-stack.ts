import { Duration, Stack, StackProps } from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as sns from "aws-cdk-lib/aws-sns";
import { Construct } from "constructs";

interface ApplicationMonitoringStackProps extends StackProps {
  apiTargetGroup: elbv2.ApplicationTargetGroup;
  applicationName: string;
  environmentName: string;
}

export class ApplicationMonitoringStack extends Stack {
  public readonly alertTopic: sns.Topic;

  constructor(
    scope: Construct,
    id: string,
    props: ApplicationMonitoringStackProps,
  ) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    this.alertTopic = new sns.Topic(this, "AlertTopic", {
      topicName: `${resourceNamePrefix}-alerts`,
    });

    const healthyHostCountAlarm = new cloudwatch.Alarm(
      this,
      "HealthyHostCountAlarm",
      {
        alarmDescription: "APIの正常なECSタスクが2分間存在しない",
        alarmName: `${resourceNamePrefix}-healthy-host-count`,
        comparisonOperator:
          cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
        evaluationPeriods: 2,
        metric: props.apiTargetGroup.metricHealthyHostCount({
          period: Duration.minutes(1),
          statistic: cloudwatch.Stats.MAXIMUM,
        }),
        threshold: 0,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      },
    );

    healthyHostCountAlarm.addAlarmAction(
      new cloudwatchActions.SnsAction(this.alertTopic),
    );
  }
}
