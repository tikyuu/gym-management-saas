import {
  Aws,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  Tags,
  aws_cloudfront as cloudfront,
  aws_cloudfront_origins as origins,
  aws_s3 as s3,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface CloudFrontStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
  frontendBucketAutoDeleteObjects: boolean;
  frontendBucketRemovalPolicy: RemovalPolicy;
  frontendBucketVersioned: boolean;
}

export class CloudFrontStack extends Stack {
  public readonly frontendBucket: s3.IBucket;

  constructor(scope: Construct, id: string, props: CloudFrontStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "cloudfront");

    this.frontendBucket = new s3.Bucket(this, "FrontendBucket", {
      autoDeleteObjects: props.frontendBucketAutoDeleteObjects,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      bucketName: `${resourceNamePrefix}-${Aws.ACCOUNT_ID}-frontend-s3`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      lifecycleRules: [
        {
          abortIncompleteMultipartUploadAfter: Duration.days(7),
        },
      ],
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      removalPolicy: props.frontendBucketRemovalPolicy,
      versioned: props.frontendBucketVersioned,
    });

    new cloudfront.Distribution(this, "FrontendDistribution", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(
          this.frontendBucket,
        ),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      defaultRootObject: "index.html",
    });
  }
}
