import { Stack, StackProps, aws_wafv2 as wafv2 } from "aws-cdk-lib";
import { Construct } from "constructs";

interface WafStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
}

export class WafStack extends Stack {
  constructor(scope: Construct, id: string, props: WafStackProps) {
    super(scope, id, props);

    const resourceName = `${props.applicationName}-${props.environmentName}-web-acl`;

    new wafv2.CfnWebACL(this, "WebAcl", {
      defaultAction: { allow: {} },
      name: resourceName,
      rules: [
        {
          name: "AmazonIpReputation",
          overrideAction: { count: {} },
          priority: 0,
          statement: {
            managedRuleGroupStatement: {
              name: "AWSManagedRulesAmazonIpReputationList",
              vendorName: "AWS",
            },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: `${resourceName}-ip-reputation`,
            sampledRequestsEnabled: false,
          },
        },
        {
          name: "KnownBadInputs",
          overrideAction: { count: {} },
          priority: 10,
          statement: {
            managedRuleGroupStatement: {
              name: "AWSManagedRulesKnownBadInputsRuleSet",
              vendorName: "AWS",
            },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: `${resourceName}-known-bad-inputs`,
            sampledRequestsEnabled: false,
          },
        },
        {
          name: "SqlInjection",
          overrideAction: { count: {} },
          priority: 20,
          statement: {
            managedRuleGroupStatement: {
              name: "AWSManagedRulesSQLiRuleSet",
              vendorName: "AWS",
            },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: `${resourceName}-sql-injection`,
            sampledRequestsEnabled: false,
          },
        },
        {
          name: "CommonRuleSet",
          overrideAction: { count: {} },
          priority: 30,
          statement: {
            managedRuleGroupStatement: {
              name: "AWSManagedRulesCommonRuleSet",
              vendorName: "AWS",
            },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: `${resourceName}-common`,
            sampledRequestsEnabled: false,
          },
        },
      ],
      scope: "CLOUDFRONT",
      visibilityConfig: {
        cloudWatchMetricsEnabled: true,
        metricName: resourceName,
        sampledRequestsEnabled: false,
      },
    });
  }
}
