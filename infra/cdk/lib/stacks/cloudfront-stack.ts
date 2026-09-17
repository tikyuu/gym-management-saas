import {
  Aws,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  Tags,
  aws_certificatemanager as acm,
  aws_cloudfront as cloudfront,
  aws_cloudfront_origins as origins,
  aws_elasticloadbalancingv2 as elbv2,
  aws_route53 as route53,
  aws_route53_targets as targets,
  aws_s3 as s3,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface CloudFrontStackProps extends StackProps {
  albOriginDomainName: string;
  applicationName: string;
  edgeCertificate: acm.ICertificate;
  environmentName: string;
  frontendBucketAutoDeleteObjects: boolean;
  frontendBucketRemovalPolicy: RemovalPolicy;
  frontendBucketVersioned: boolean;
  frontendDomainName: string;
  hostedZoneId: string;
  hostedZoneName: string;
  internalAlb: elbv2.IApplicationLoadBalancer;
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

    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(
      this,
      "HostedZone",
      {
        hostedZoneId: props.hostedZoneId,
        zoneName: props.hostedZoneName,
      },
    );

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

    const apiOrigin = origins.VpcOrigin.withApplicationLoadBalancer(
      props.internalAlb,
      {
        domainName: props.albOriginDomainName,
        protocolPolicy: cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
      },
    );

    const distribution = new cloudfront.Distribution(this, "FrontendDistribution", {
      certificate: props.edgeCertificate,
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(
          this.frontendBucket,
        ),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
      },
      defaultRootObject: "index.html",
      domainNames: [props.frontendDomainName],
    });

    new route53.ARecord(this, "FrontendAliasRecord", {
      recordName: props.frontendDomainName,
      target: route53.RecordTarget.fromAlias(
        new targets.CloudFrontTarget(distribution),
      ),
      zone: hostedZone,
    });

    new route53.AaaaRecord(this, "FrontendIpv6AliasRecord", {
      recordName: props.frontendDomainName,
      target: route53.RecordTarget.fromAlias(
        new targets.CloudFrontTarget(distribution),
      ),
      zone: hostedZone,
    });
  }
}
