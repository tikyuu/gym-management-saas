import {
  Aws,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_cloudtrail as cloudtrail,
  aws_s3 as s3,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface AuditStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
  frontendBucket: s3.IBucket;
}

export class AuditStack extends Stack {
  constructor(scope: Construct, id: string, props: AuditStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    const cloudTrailLogBucket = new s3.Bucket(this, "CloudTrailLogBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      bucketName: `${resourceNamePrefix}-${Aws.ACCOUNT_ID}-cloudtrail-logs-s3`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      lifecycleRules: [
        {
          expiration: Duration.days(365),
          noncurrentVersionExpiration: Duration.days(1),
        },
      ],
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      removalPolicy: RemovalPolicy.RETAIN,
      versioned: true,
    });

    const trail = new cloudtrail.Trail(this, "Trail", {
      bucket: cloudTrailLogBucket,
      enableFileValidation: true,
      includeGlobalServiceEvents: true,
      isMultiRegionTrail: true,
      managementEvents: cloudtrail.ReadWriteType.ALL,
      trailName: `${resourceNamePrefix}-trail`,
    });

    const cloudFormationTrail = trail.node.defaultChild as cloudtrail.CfnTrail;

    cloudFormationTrail.addPropertyDeletionOverride("EventSelectors");
    cloudFormationTrail.advancedEventSelectors = [
      {
        fieldSelectors: [
          {
            equalTo: ["Management"],
            field: "eventCategory",
          },
        ],
        name: "LogManagementEvents",
      },
      {
        fieldSelectors: [
          {
            equalTo: ["Data"],
            field: "eventCategory",
          },
          {
            equalTo: ["AWS::S3::Object"],
            field: "resources.type",
          },
          {
            equalTo: ["PutObject", "DeleteObject"],
            field: "eventName",
          },
          {
            field: "resources.ARN",
            startsWith: [`${props.frontendBucket.bucketArn}/`],
          },
        ],
        name: "LogFrontendS3Writes",
      },
    ];
  }
}
