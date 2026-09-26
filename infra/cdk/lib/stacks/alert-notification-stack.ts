import { Stack, StackProps, Tags, aws_sns as sns } from "aws-cdk-lib";
import { Construct } from "constructs";

interface AlertNotificationStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
}

export class AlertNotificationStack extends Stack {
  public readonly alertTopic: sns.ITopic;

  constructor(
    scope: Construct,
    id: string,
    props: AlertNotificationStackProps,
  ) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "alert-notification");

    this.alertTopic = new sns.Topic(this, "AlertTopic", {
      topicName: `${resourceNamePrefix}-alerts`,
    });
  }
}
