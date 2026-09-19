import {
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_logs as logs,
  aws_wafv2 as wafv2,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface WafStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
}

export class WafStack extends Stack {
  public readonly webAclArn: string;

  constructor(scope: Construct, id: string, props: WafStackProps) {
    super(scope, id, props);

    const resourceName = `${props.applicationName}-${props.environmentName}-web-acl`;

    const wafLogGroup = new logs.LogGroup(this, "WafLogGroup", {
      logGroupName: `aws-waf-logs-${props.applicationName}-${props.environmentName}`,
      removalPolicy: RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.TWO_MONTHS,
    });

    const webAcl = new wafv2.CfnWebACL(this, "WebAcl", {
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
        {
          action: { count: {} },
          name: "ApiRateLimit",
          priority: 40,
          statement: {
            rateBasedStatement: {
              aggregateKeyType: "IP",
              evaluationWindowSec: 300,
              limit: 3000,
              scopeDownStatement: {
                byteMatchStatement: {
                  fieldToMatch: { uriPath: {} },
                  positionalConstraint: "STARTS_WITH",
                  searchString: "/api/",
                  textTransformations: [{ priority: 0, type: "NONE" }],
                },
              },
            },
          },
          visibilityConfig: {
            cloudWatchMetricsEnabled: true,
            metricName: `${resourceName}-api-rate-limit`,
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

    this.webAclArn = webAcl.attrArn;

    new wafv2.CfnLoggingConfiguration(this, "LoggingConfiguration", {
      logDestinationConfigs: [wafLogGroup.logGroupArn],
      redactedFields: [
        {
          singleHeader: {
            name: "authorization",
          },
        },
        {
          singleHeader: {
            name: "cookie",
          },
        },
      ],
      resourceArn: webAcl.attrArn,
    });
  }
}
