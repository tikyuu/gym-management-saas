import { Stack, StackProps } from "aws-cdk-lib";
import * as sns from "aws-cdk-lib/aws-sns";
import { Construct } from "constructs";

interface EdgeMonitoringStackProps extends StackProps {
  applicationName: string;
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
  }
}
