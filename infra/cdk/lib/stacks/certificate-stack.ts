import {
  Stack,
  StackProps,
  Tags,
  aws_certificatemanager as acm,
  aws_route53 as route53,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface CertificateStackProps extends StackProps {
  applicationName: string;
  domainName: string;
  environmentName: string;
  hostedZoneId: string;
  hostedZoneName: string;
  subjectAlternativeNames?: string[];
}

export class CertificateStack extends Stack {
  public readonly certificate: acm.ICertificate;

  constructor(scope: Construct, id: string, props: CertificateStackProps) {
    super(scope, id, props);

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "certificate");

    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(
      this,
      "HostedZone",
      {
        hostedZoneId: props.hostedZoneId,
        zoneName: props.hostedZoneName,
      },
    );

    this.certificate = new acm.Certificate(this, "Certificate", {
      domainName: props.domainName,
      subjectAlternativeNames: props.subjectAlternativeNames,
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });
  }
}
