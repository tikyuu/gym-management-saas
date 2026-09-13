import {
  RemovalPolicy,
  Stack,
  StackProps,
  Tags,
  aws_cognito as cognito,
} from "aws-cdk-lib";
import { Construct } from "constructs";
import { CustomerAuthenticationConstruct } from "../constructs/authentication/customer-authentication-construct";

interface AuthenticationStackProps extends StackProps {
  applicationName: string;
  customerOAuthCallbackUrls: string[];
  customerOAuthLogoutUrls: string[];
  customerUserPoolDomainPrefix: string;
  environmentName: string;
  removalPolicy: RemovalPolicy;
  userPoolDeletionProtection: boolean;
}

export class AuthenticationStack extends Stack {
  public readonly customerAppClient: cognito.IUserPoolClient;
  public readonly customerUserPool: cognito.IUserPool;

  constructor(scope: Construct, id: string, props: AuthenticationStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "authentication");

    const customerAuthentication = new CustomerAuthenticationConstruct(
      this,
      "CustomerAuthentication",
      {
        customerOAuthCallbackUrls: props.customerOAuthCallbackUrls,
        customerOAuthLogoutUrls: props.customerOAuthLogoutUrls,
        customerUserPoolDomainPrefix: props.customerUserPoolDomainPrefix,
        removalPolicy: props.removalPolicy,
        resourceNamePrefix,
        userPoolDeletionProtection: props.userPoolDeletionProtection,
      },
    );

    this.customerAppClient = customerAuthentication.appClient;
    this.customerUserPool = customerAuthentication.userPool;
  }
}
