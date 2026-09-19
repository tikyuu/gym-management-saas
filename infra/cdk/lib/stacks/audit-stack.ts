import {
  Aws,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_s3 as s3,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface AuditStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
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
  }
}
